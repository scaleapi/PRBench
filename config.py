import yaml
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Config:
    
    judge_model_name: str
    filename: str
    base_url: str
    litellm_key_path: str
    trial_number: int = 0
    debug: bool = False
    web_search: bool = False
    background: bool = False
    timeout_seconds: int = 300  # 5 minutes default
    final_response_source: str = "prefilled" # "prefilled" or "sampled" or "part_of_conversation"
    prefilled_response_column: str = None
    previous_output_json: str = None
    cache: bool = False
    response_api: str = "responses" # "responses" or "chat.completions"
    response_model_names: List[str] = field(default_factory=list)
    reasoning_effort_by_model: Dict[str, str] = field(default_factory=dict)
    thinking_budget_by_model: Dict[str, int] = field(default_factory=dict)
    
    def get_litellm_key(self) -> str:
        with open(self.litellm_key_path, 'r') as f:
            return f.read().strip()
    
    def get_thinking_config_for_extra_body(self, model_name: str) -> Optional[Dict]:
        """Get thinking configuration formatted for extra_body parameter.
        
        For Gemini models, returns the thinking config in the format:
        {'google': {'thinking_config': {'thinking_budget': N, 'include_thoughts': True}}}
        """
        if model_name in self.thinking_budget_by_model:
            return {
                'google': {
                    'thinking_config': {
                        'thinking_budget': self.thinking_budget_by_model[model_name],
                        'include_thoughts': True
                    }
                }
            }
        return None
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'Config':
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary for serialization."""
        return {
            'judge_model_name': self.judge_model_name,
            'filename': self.filename,
            'base_url': self.base_url,
            'litellm_key_path': self.litellm_key_path,
            'debug': self.debug,
            'web_search': self.web_search,
            'background': self.background,
            'response_api': self.response_api,
            'timeout_seconds': self.timeout_seconds,
            'response_model_names': self.response_model_names,
            'reasoning_effort_by_model': self.reasoning_effort_by_model,
            'thinking_budget_by_model': self.thinking_budget_by_model,
            'prefilled_response_column': self.prefilled_response_column,
            'previous_output_json': self.previous_output_json,
            'cache': self.cache,
        }
    
    def to_yaml(self, yaml_path: str) -> None:
        """Save configuration to a YAML file."""
        with open(yaml_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)
    
    def get_debug_response_models(self) -> List[str]:
        if self.debug:
            return [self.response_model_names[0]]
        return self.response_model_names
