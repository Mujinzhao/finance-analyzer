import os

# DeepSeek first, with legacy Anthropic env vars as fallback for compatibility.
DEEPSEEK_API_KEY = (
	os.environ.get("DEEPSEEK_API_KEY", "sk-d98da1e0972741b7aa2952731733ca03")
	or os.environ.get("OPENAI_API_KEY", "")
	or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
	or os.environ.get("ANTHROPIC_API_KEY", "")
)
DEEPSEEK_BASE_URL = (
	os.environ.get("DEEPSEEK_BASE_URL", "")
	or os.environ.get("OPENAI_BASE_URL", "")
	or os.environ.get("ANTHROPIC_BASE_URL", "")
	or "https://api.deepseek.com"
)
DEEPSEEK_MODEL = (
	os.environ.get("DEEPSEEK_MODEL", "")
	or os.environ.get("OPENAI_MODEL", "")
	or os.environ.get("CLAUDE_MODEL", "")
	or "deepseek-chat"
)
