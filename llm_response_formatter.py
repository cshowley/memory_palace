"""Prompt for LLM response"""

"""Generate response based on last set of received user messages, then rewrite response into text-message format for UX clarify"""

prompt = """Rewrite the last message in the format of a series of text messages, each no more than 280 characters. Minimal use of emojis and slang."""
