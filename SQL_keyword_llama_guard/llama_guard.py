import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import jinja2
from SQL_keyword_llama_guard.utils import split_content, log_error

class LlamaGuard:
    def __init__(self, debug_mode=False):
        """
        Initializes the LlamaGuard with necessary models and tokenizer.
        
        Args:
        debug_mode (bool): Whether to enable debug logging.
        """
        self.debug_mode = debug_mode
        try:
            # Load Llama model and tokenizer
            self.llama_model, self.llama_tokenizer = self.load_llama_model()
            self.chat_template = self.llama_tokenizer.chat_template  #從tokenizer_config.json讀取
        except Exception as e:
            log_error("Failed to load Llama model", e, self.debug_mode)

    def load_llama_model(self):
        """
        Loads the Llama model and tokenizer.
        
        Returns:
        tuple: The loaded model and tokenizer.
        """
        model_id = "meta-llama/Llama-Guard-3-8B"
        device = "cuda"
        dtype = torch.bfloat16
        quantization_config = BitsAndBytesConfig(load_in_8bit=True)

        try:
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype, device_map=device, quantization_config=quantization_config)
            return model, tokenizer
        except Exception as e:
            log_error("Failed to load Llama model or tokenizer", e, self.debug_mode)
            return None, None

    def render_chat_template(self, messages):
        """
        Renders the chat template using Jinja2 with the provided messages.
        
        Args:
        messages (list): A list of messages to format using the chat template.

        Returns:
        str: The rendered chat template.
        """
        try:
            template = jinja2.Template(self.chat_template)
            rendered_template = template.render(messages=messages)
            return rendered_template
        except Exception as e:
            log_error("Failed to render chat template", e, self.debug_mode)
            return ""

    def moderate(self, chat):
        """
        Moderates the provided chat content using the Llama model.
        
        Args:
        chat (list): The conversation messages to moderate.

        Returns:
        str: The moderation result.
        """
        try:
            formatted_chat = self.render_chat_template(chat)
            #print(formatted_chat)
            input_ids = self.llama_tokenizer(formatted_chat, return_tensors="pt").input_ids.to("cuda")
            output = self.llama_model.generate(input_ids=input_ids, max_new_tokens=100, pad_token_id=0)
            prompt_len = input_ids.shape[-1]
            return self.llama_tokenizer.decode(output[0][prompt_len:], skip_special_tokens=True)
        except Exception as e:
            log_error("Error during moderation", e, self.debug_mode)
            return ""

    def get_feedback(self, text):
        """
        Processes the provided text by splitting it into chunks and moderating each chunk.
        
        Args:
        text (str): The content to be moderated.

        Returns:
        list: A list of feedback tuples for each content chunk.
        """
        try:
            chunks = split_content(text)
            feedbacks = []
            for chunk in chunks:
                feedback = self.moderate([
                    {"role": "user", "content": ""},  # Placeholder for user input
                    {"role": "assistant", "content": chunk}
                ])
                feedback_lines = [line.strip() for line in feedback.splitlines() if line.strip()]
                safe = 1 if len(feedback_lines) > 0 and feedback_lines[0].lower() == "safe" else 0
                classification = feedback_lines[1] if len(feedback_lines) > 1 and safe != 1 else None
                feedbacks.append((safe, classification))
            return feedbacks
        except Exception as e:
            log_error("Error in KeywordGuard processing", e, self.debug_mode)
            return [(0, "error")]  # Return error feedback if an exception occurs