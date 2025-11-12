import os
import pdb
import asyncio
import json
import pandas as pd
from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple, Union, Any
from tqdm import tqdm
from openai import AsyncOpenAI
from constants import GRADER_TEMPLATE, GRADE_MAP
from criteria import Criterion
from tqdm.asyncio import tqdm_asyncio
from config import Config
from copy import deepcopy
from time import sleep
import hashlib
from diskcache import Cache
import re


MAX_RETRIES = 5
RETRY_BACKOFF_SECONDS = 2
DEFAULT_CACHE_NAMESPACE = "default"
TOTAL_QUERY_COUNT = 0
TOTAL_CACHE_HIT_COUNT = 0
PRINT_EVERY_N_QUERIES = 500


def _make_cache_key(model_name: str, prompt: Union[str, Dict[str, Any]], kwargs: Dict[str, Any]) -> str:
    k = dict(kwargs or {})
    k.pop("background", None)

    payload = {
        "model": model_name,
        "input": prompt,
        "kwargs": k,
    }
    blob = json.dumps(payload, sort_keys=True, default=str)
    key = hashlib.sha256(blob.encode("utf-8")).hexdigest()

    return key


def _cache_get(key: str, cache: Cache):
    return cache.get(key)


def _cache_set(key: str, value: str, cache: Cache):
    if value and isinstance(value, str):
        cache.set(key, value)


async def async_query_background(client, model_name, prompt, kwargs_instance, timeout_seconds):
    resp = await client.responses.create(
        model=model_name,
        input=prompt,
        background=True,
        **kwargs_instance
    )
    count = 0
    while getattr(resp, "status", None) in {"queued", "in_progress"}:
        # if count % 300 == 0:
        #     print(f"Current status: {resp.status}")
        await asyncio.sleep(2)
        count += 1
        resp = await client.responses.retrieve(resp.id)

    return resp


async def async_query_foreground(client, model_name, prompt, kwargs_instance, timeout_seconds, response_api: str = "responses"):
    if response_api == "responses":
        resp = await client.responses.create(
            model=model_name,
            input=prompt,
            **kwargs_instance
        )
        return resp
    else:
        resp = await client.chat.completions.create(
            model=model_name,
            messages=prompt,
            **kwargs_instance
        )
        return resp


async def async_query(client, sem, model_name, prompt: Union[str, Dict[str, Any]], kwargs={}, 
                      timeout_seconds: int = 300, background: bool = False, cache: Cache = None,
                      response_api: str = "responses") -> str:

    kwargs_instance = deepcopy(kwargs)

    global TOTAL_QUERY_COUNT
    global TOTAL_CACHE_HIT_COUNT
    TOTAL_QUERY_COUNT += 1

    if TOTAL_QUERY_COUNT % PRINT_EVERY_N_QUERIES == 0:
        cache_hit_rate = TOTAL_CACHE_HIT_COUNT / TOTAL_QUERY_COUNT
        print(f"Total query count: {TOTAL_QUERY_COUNT}. Total cache hit count: {TOTAL_CACHE_HIT_COUNT}. Cache hit rate: {cache_hit_rate:.2f}.")
    

    # Cache lookup
    cache_key = None
    if cache is not None:
        cache_key = _make_cache_key(model_name, prompt, kwargs_instance)
        cached = _cache_get(cache_key, cache)
        if cached is not None and isinstance(cached, str):
            TOTAL_CACHE_HIT_COUNT += 1
            return cached

    # Query
    response = None
    for attempt in range(MAX_RETRIES):
        try:
            # Limit concurrent requests
            async with sem:
                response = await asyncio.wait_for(
                    async_query_background(
                        client, model_name, prompt, kwargs_instance, timeout_seconds
                    ) if background else async_query_foreground(
                        client, model_name, prompt, kwargs_instance, timeout_seconds, response_api
                    ),
                    timeout=timeout_seconds
                )
            break
        
        except Exception as e:
            error = str(e)
            print(f"Attempt {attempt+1} failed: ", error)

            # Back off reasoning effort if it was high and this is the second to last attempt
            if "reasoning" in kwargs_instance and attempt == MAX_RETRIES - 2:
                print(f"Reasoning effort was {kwargs_instance['reasoning']['effort']}, setting to low")
                kwargs_instance["reasoning"]["effort"] = "low"
            
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    
    if response:
        try:
            out = getattr(response, "output_text", None)
            # out = response.choices[0].message.content
        except TypeError as e:
            print(f"Error getting output text: {e}")
            out = None
        if out is None:
            # Print the response
            print(f"Response: {response}")
            out = "N/A"
        # Update cache
        if cache is not None and cache_key and out and out != "N/A":
            _cache_set(cache_key, out, cache)

        return out if out is not None else "N/A"

    return "N/A"


async def grade_final_response(client, sem, model_name, conversation: str, rubric: List[str], timeout_seconds: int = 300, cache: Cache = None):
    tasks = []
    for criterion in rubric:
        prompt = GRADER_TEMPLATE.replace("<<rubric_item>>", criterion)
        prompt = prompt.replace("<<conversation>>", conversation)
        task = asyncio.create_task(async_query(client, sem, model_name, prompt, timeout_seconds=timeout_seconds, cache=cache))
        tasks.append(task)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    results = [get_criteria_met(res) for res in results]
    return results


async def get_total_points(client, sem, judge_model_name, convos, rubrics_texts, weights, timeout_seconds: int = 300, cache: Cache = None):
    tasks = [
        grade_final_response(client, sem, judge_model_name, c, r, timeout_seconds=timeout_seconds, cache=cache) 
        for c, r in zip(convos, rubrics_texts)
    ]
    print("Grading final response")
    grades = await tqdm_asyncio.gather(*tasks)
    points = [sum([GRADE_MAP[g]*w for g, w in zip(grade, weight)]) for grade, weight in zip(grades, weights)]
    return grades, points


async def get_final_response(client, sem, response_model_name, convos, kwargs, timeout_seconds: int = 300, background: bool = False, cache: Cache = None, response_api: str = "responses"):
    prompts = [
        [{"role": role, "content": content} for role, content in convo]
        for convo in convos
    ]
    print(f"Getting final response for {response_model_name}")
    tasks = [async_query(client, sem, response_model_name, prompt, kwargs, timeout_seconds=timeout_seconds, background=background, cache=cache, response_api=response_api) for prompt in prompts]
    final_responses = await tqdm_asyncio.gather(*tasks)
    return final_responses


async def list_query(client, sem, model_name, prompts: List[str], kwargs={}, timeout_seconds: int = 300, background: bool = False, cache: Cache = None, response_api: str = "responses"):
    tasks = [async_query(client, sem, model_name, prompt, kwargs, timeout_seconds=timeout_seconds, background=background, cache=cache, response_api=response_api) for prompt in prompts]
    results = await tqdm_asyncio.gather(*tasks)
    return results


def get_criteria_met(response):

    if response == "N/A":
        print(f"Grading timed out")
        return "false"

    if not isinstance(response, str):
        print(f"Response is not a string: {response}")
        return "false"

    grade = response.split('criteria_met":')[-1].split("\n")[0].strip()

    if "true" in grade.lower() and "false" in grade.lower():
        print(f"Unknown grade for response: {response}")
        return "false"
    if "true" in grade.lower():
        return "true"
    elif "false" in grade.lower():
        return "false"
    else:
        print(f"Unknown grade for response: {response}")
        return "false"


def create_convo(convo: List[Tuple[str, str]]):
    s = ""
    for speaker, statement in convo:
        s += speaker + ": "
        try:
            s += statement + "\n"
        except Exception as e:
            print(f"Error creating convo: {e}")
            s += "N/A" + "\n"
            # return None
    return s.strip()


def extract_rubric(row):
    rubric = row['rubric']
    return [Criterion(c) for c in rubric]


def get_normalized_points(point_total, weights):
    min_weight = sum([w for w in weights if w < 0])
    max_weight = sum([w for w in weights if w > 0])
    return (point_total - min_weight) / (max_weight - min_weight)


def get_clipped_points(point_total, weights):
    max_weight = sum([w for w in weights if w > 0])
    return point_total / max_weight


def kwargs_for(model_name: str, config: Config) -> Dict:
    args = {}

    if model_name in config.reasoning_effort_by_model:
        args["reasoning"] = {"effort": config.reasoning_effort_by_model[model_name]}

    if config.web_search:
        args["tools"] = [{"type": "web_search"}]

    # Thinking budget needs to be passed via extra_body for Gemini/Claude models
    if "gemini" in model_name:
        thinking_config = config.get_thinking_config_for_extra_body(model_name)
        if thinking_config:
            args["extra_body"] = thinking_config

    if "claude" in model_name:
        args["extra_body"] = {"thinking": {"type": "enabled", "budget_tokens": config.thinking_budget_by_model[model_name]}}

    # if config.cache:
    #     if "extra_body" in args:
    #         args["extra_body"]["cache"] = {"namespace": "pro_rubrics_trial_" + str(config.trial_number)}
    #     else:
    #         args["extra_body"] = {"cache": {"namespace": "pro_rubrics_trial_" + str(config.trial_number)}}

    print("Arguments for model: ", model_name, " are: ", args)
    return args

def decision_type_to_json(response):
    if response == "N/A":
        print(f"Decision type timed out")
        return {
            "primary": {"code": "N/A", "label": "N/A"},
            "secondary": []
        }
    
    try:
        json_object = response.split("```json")[1].split("```")[0].strip()
        return json.loads(json_object)
    except Exception as e:
        print(f"Error parsing JSON for decision type: {response}")
        print(f"Error message: {e}")
        return {
            "primary": {"code": "N/A", "label": "N/A"},
            "secondary": []
        }

def economic_pathway_to_json(response):
    if response == "N/A":
        print(f"Economic pathway timed out")
        return {
            "primary": {"code": "N/A", "label": "N/A"},
            "secondary": []
        }
    
    try:
        json_object = response.split("```json")[1].split("```")[0].strip()
        return json.loads(json_object)
    except Exception as e:
        print(f"Error message: {e}")
        print(f"for response: {response}")
        return {
            "primary": {"code": "N/A", "label": "N/A"},
            "secondary": []
        }

def process_reference_texts(row):
    for col in row.keys():
        if "reference" in col:
            if isinstance(row[col], list):
                print(f"Processing reference texts for task: {row['task']} in column: {col}, count: {len(row[col])}")
                reference_texts = row[col]
                col_num = col.split("_")[-1]
                reference_text_body = ""
                for i in range(len(reference_texts)):
                    reference_text_body += f"Reference Text {i}:\n{reference_texts[i]}\n\n"
                row[f"prompt_{col_num}"] = reference_text_body + row[f"prompt_{col_num}"]
    return row

def remove_thinking_tags(text: str) -> str:
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<reason>.*?</reason>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # remove excessive whitespace
    text = text.strip()
    return text
