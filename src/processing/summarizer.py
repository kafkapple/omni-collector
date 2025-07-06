import os
import google.generativeai as genai
from dotenv import load_dotenv
from omegaconf import DictConfig, OmegaConf # Import OmegaConf for config handling

class Summarizer:
    def __init__(self, enabled: bool, prompts: dict, save_raw_content: bool = False, **kwargs):
        load_dotenv()
        self.enabled = enabled
        self.prompts = prompts # prompts 딕셔너리 받음
        self.save_raw_content = save_raw_content
        self.model = None
        if os.getenv("GEMINI_API_KEY"):
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            print("Warning: GEMINI_API_KEY not found. Summarizer will not work.")

    def _get_prompt_text(self, selected_prompt_name: str, text: str) -> str:
        """Retrieves and formats the prompt text."""
        if selected_prompt_name not in self.prompts:
            print(f"Warning: Prompt '{selected_prompt_name}' not found. Using 'basic' prompt.")
            selected_prompt_name = 'basic' # Fallback to basic

        prompt_template = self.prompts.get(selected_prompt_name, self.prompts['basic'])
        return prompt_template.format(text=text)

    def process_item(self, item: dict, selected_prompt_name: str) -> dict:
        """Processes a single item for summarization."""
        if not self.model or 'body' not in item or not item['body']:
            item['summary'] = ""
            if not self.save_raw_content:
                item.pop('body', None)
            return item

        try:
            prompt_text = self._get_prompt_text(selected_prompt_name, item['body'])
            response = self.model.generate_content(prompt_text)
            item['summary'] = response.text
        except Exception as e:
            print(f"Error summarizing item {item.get('title')}: {e}")
            item['summary'] = "요약 생성 중 오류 발생"
        
        if not self.save_raw_content:
            item.pop('body', None)
        return item

    def summarize_data(self, data_list: list[dict], selected_prompt_name: str, progress_callback=None) -> list[dict]:
        """
        Summarizes a list of data items using the specified prompt.
        
        Args:
            data_list: A list of dictionaries, where each dictionary represents an item to summarize.
                       Each item must have a 'body' key containing the text to be summarized.
            selected_prompt_name: The name of the prompt to use from the 'prompts' dictionary.
            progress_callback: An optional function to call with current progress (e.g., for UI updates).
                               It should accept two arguments: current_index and total_items.
        
        Returns:
            A list of dictionaries with 'summary' added to each item.
        """
        if not self.enabled:
            print("Summarization is disabled. Skipping.")
            return data_list

        summarized_items = []
        total_items = len(data_list)
        for i, item_data in enumerate(data_list):
            summarized_item = self.process_item(item_data, selected_prompt_name)
            summarized_items.append(summarized_item)
            if progress_callback:
                progress_callback(i + 1, total_items)
        return summarized_items