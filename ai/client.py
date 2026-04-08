import base64
import json
from config import AIConfig


def create_client(config: AIConfig):
    """根据配置创建 AI 客户端。"""
    if config.provider == "claude":
        return ClaudeClient(config)
    return OpenAICompatibleClient(config)


class OpenAICompatibleClient:
    """OpenAI 兼容协议客户端（支持大多数国产模型）。"""

    def __init__(self, config: AIConfig):
        from openai import OpenAI
        self.client = OpenAI(api_key=config.api_key, base_url=config.api_url)
        self.model = config.model_name

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def chat_with_images(self, text: str, images_base64: list[str], temperature: float = 0.3) -> str:
        content = [{"type": "text", "text": text}]
        for img in images_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img}"},
            })
        messages = [{"role": "user", "content": content}]
        return self.chat(messages, temperature)


class ClaudeClient:
    """Anthropic Claude 客户端。"""

    def __init__(self, config: AIConfig):
        import anthropic
        self.client = anthropic.Anthropic(api_key=config.api_key)
        self.model = config.model_name

    def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        # 将 OpenAI 格式的 messages 转换为 Claude 格式
        claude_messages = []
        system_text = ""
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                claude_messages.append(msg)

        kwargs = {"model": self.model, "max_tokens": 8192, "messages": claude_messages, "temperature": temperature}
        if system_text:
            kwargs["system"] = system_text.strip()

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def chat_with_images(self, text: str, images_base64: list[str], temperature: float = 0.3) -> str:
        content = [{"type": "text", "text": text}]
        for img in images_base64:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img},
            })
        messages = [{"role": "user", "content": content}]
        return self.chat(messages, temperature)
