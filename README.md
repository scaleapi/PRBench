# PRBench: Professional Reasoning Benchmark

> A lightweight evaluation harness for PRBench, a large-scale expert-annotated benchmark for high-stakes reasoning in professional domains. Current version covers Legal and Finance domains.

This repository provides the code necessary to run rubric-based evaluations using the PRBench dataset and pipeline. The main entry point is evals.py, which conducts model response generation, automated scoring via an LLM-judge, caching, retries, and reporting.

PRBench consists of:

* 1,100 expert-authored conversations across Finance and Legal domains

* 19,356 expert-curated rubric criteria (10–30 per task)

* Coverage of 114 countries, 47 U.S. jurisdictions, and 25 total professional topics.

* Hard subsets (Finance-300, Legal-250) representing the most challenging tasks

See the paper for full details.


## Quickstart

1. Install dependencies in `requirements.txt`
2. Set API key, url for the endpoint to sample responses from and model grading.
3. Configure the config.yaml to point to the right API key path `litellm_key_path` and base url. The code uses OpenAI SDK--make sure to use the right key for your endpoint.
4. Select which response models to evaluate in `response_model_names`.
5. For debugging set `debug` to `true` which will only run evaluation for the first 2 samples.
6. Run with `python evals.py --config config.yaml`.

## Source of Responses

By default, the script will sample responses to the conversations from the models listed under `response_model_names` when `final_response_source` is set as `sampled`. Alternatively, setting `final_response_source: prefilled`, will load responses from `filename`.json. Format the json to be `task->response`.

## Outputs

Results are saved under `results/`. We report `mean_clipped` scores in the paper. Results for individual data points may be found under `outputs`.

## Acknowledgments

We are grateful to the domain experts who contributed their time and expertise to PRBench.
