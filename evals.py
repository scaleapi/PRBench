import pandas as pd
from util import *
import numpy as np
import pdb
import asyncio
from tqdm.asyncio import tqdm_asyncio
from collections import defaultdict
import datetime
import json
from config import Config
import sys
from datasets import load_dataset


async def load_process_csv_data_custom_responses(
    client, judge_model_name, response_model_name, kwargs,
    config: Config
):
    df = load_dataset("ScaleAI/PRBench", split=config.split_name).to_pandas()
    if config.debug:
        df = df[10:12]

    response_model_name_short = response_model_name.split("/")[-1]
    judge_model_name_short = judge_model_name.split("/")[-1]
    _RESP_CACHE = Cache(f"./cache/responses_cache_response_{response_model_name_short}_trial_{config.trial_number}")
    _GRADES_CACHE = Cache(f"./cache/grades_cache_judge_{judge_model_name_short}_response_{response_model_name_short}_trial_{config.trial_number}")

    # Prepend reference texts to prompts
    df = df.apply(process_reference_texts, axis=1)

    sem = asyncio.Semaphore(64)

    def process_row_get_convo(row):
        convo = []
        for i in range(10):
            prompt_col = f"prompt_{i}"
            if prompt_col in row and type(row[prompt_col]) == str and len(row[prompt_col].strip()) > 0:
                convo.append(("user", row[prompt_col]))
            response_col = f"response_{i}"
            if response_col in row and type(row[response_col]) == str and len(row[response_col].strip()) > 0:
                convo.append(("assistant", row[response_col]))
        return convo

    convos = df.apply(process_row_get_convo, axis=1).tolist() # list of tuples

    # Retrieve final responses
    if config.final_response_source == "prefilled":
        final_responses = json.load(open(f"{config.filename}.json"))
        final_responses = {k: remove_thinking_tags(v) for k, v in final_responses.items()}
        final_responses_list = []
        for task in df['task']:
            final_responses_list.append(final_responses[task])
        convos = [create_convo([t for t in convo] + [("assistant", final_response)]) for convo, final_response in zip(convos, final_responses_list)]
    
    # Sample final responses
    elif config.final_response_source == "sampled":
        final_responses = await get_final_response(
            client, sem, response_model_name, convos, kwargs, 
            timeout_seconds=config.timeout_seconds, background=config.background, 
            cache=_RESP_CACHE, response_api=config.response_api
        )
        final_responses = [remove_thinking_tags(s) for s in final_responses]
        convos = [create_convo([t for t in convo] + [("assistant", final_response)]) for convo, final_response in zip(convos, final_responses)]
    
    # Scrape final responses from an output file
    elif config.final_response_source == "part_of_conversation":
        # Full convos are available in the previous output json.
        with open(config.previous_output_json, "r") as f:
            data = json.load(f)
        convos = [item['convo'] for task, item in data[response_model_name].items]

        # IDs should be aligned.
        output_ids = [task for task, _ in data[response_model_name].items]
        assert output_ids == df['task'].tolist()

    else:
        raise ValueError(f"Invalid final response source: {config.final_response_source}")

    # Collate convos final responses and other data
    rubrics = df[['rubric', 'field']].apply(extract_rubric, axis=1)
    ids = df['task'].tolist()
    fields = df['field'].tolist()
    rubrics_texts = [[c.get_title() for c in rubric] for rubric in rubrics]
    weights = [[c.get_weight() for c in rubric] for rubric in rubrics]
    categories = [[c.get_category() for c in rubric] for rubric in rubrics]

    # Calculate grades and points
    grades, points = await get_total_points(client, sem, judge_model_name, convos, rubrics_texts, weights, cache=_GRADES_CACHE)
    normalized_points = [get_normalized_points(p, weight) for p, weight in zip(points, weights)]
    clipped_points = [get_clipped_points(p, weight) for p, weight in zip(points, weights)]
    outputs = [
        {
            "convo": convo,
            "id": idx,
            "grades": g,
            "points": p,
            "categories": c,
            "weights": w,
            "rubric_texts": r,
            "field": f
        } for convo, g, p, c, w, r, idx, f in zip(convos, grades, points, categories, weights, rubrics_texts, ids, fields)
    ]
    return normalized_points, clipped_points, outputs

async def run_evals_off_platform(config: Config):

    results = defaultdict(dict)
    response_model_names = config.get_debug_response_models()
    if config.background:
        assert config.response_api == "responses"

    # Create global cache for responses and grades based on trial number
    if config.cache:
        os.makedirs("./cache", exist_ok=True)
        

    async with AsyncOpenAI(api_key=config.get_litellm_key(), base_url=config.base_url) as client:
        for response_model_name in response_model_names:
            normalized_points, clipped_points, outputs = await load_process_csv_data_custom_responses(
                client,
                config.judge_model_name,
                response_model_name,
                kwargs=kwargs_for(response_model_name, config),
                config=config
            )

            results["mean_normalized"][response_model_name] = np.mean(normalized_points)
            results["std_normalized"][response_model_name] = np.std(normalized_points)
            results["points_normalized"][response_model_name] = normalized_points

            results["mean_clipped"][response_model_name] = max(0, np.mean(clipped_points))
            results["std_clipped"][response_model_name] = np.std(clipped_points)
            results["points_clipped"][response_model_name] = clipped_points

            outputs_dict = {}
            for o in outputs:
                outputs_dict[o["id"]] = o
            results["outputs"][response_model_name] = outputs_dict

    # Save config along with results
    results["config"] = config.to_dict()
    
    # Generate output filename and save results
    judge_model_name_short = config.judge_model_name.split("/")[-1]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("results", exist_ok=True)
    output_filename = (
        f"results/{config.filename.split('/')[-1]}_off_platform_judge_{judge_model_name_short}"
        f"_web_search_{config.web_search}_debug_{config.debug}"
        f"_trial_{config.trial_number}_cache_{config.cache}_{timestamp}.json"
    )
    
    with open(output_filename, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_filename}")
    print("Mean (normalized): ", results["mean_normalized"])
    print("Mean (clipped): ", results["mean_clipped"])

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    config = Config.from_yaml(config_path)
    asyncio.run(run_evals_off_platform(config))