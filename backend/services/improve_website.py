import anthropic
import json
import re
from dotenv import load_dotenv
import os
import re

load_dotenv()

class ImproveWebsite: 
  def __init__(self, dict_web_crawl) : 

    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API"))
    self.dict_web_crawl = dict_web_crawl
    self.client = client

  def clean_markdown(self, markdown: str) -> str:
    # Remove SVG image tags (they're just placeholders)
    markdown = re.sub(r'!\[.*?\]\(data:image/svg\+xml.*?\)', '', markdown)
    # Remove navigation link blocks
    markdown = re.sub(r'\[.*?\]\(https://4ipgroup\.com/.*?\)', '', markdown)
    return markdown.strip()

  def optimize_seo_with_claude(self) :

    cleaned_input = self.dict_web_crawl
    cleaned_input["markdown_content"] = self.clean_markdown(self.dict_web_crawl["markdown_content"]) # Modify just the mardown

    prompt = f"""
You are an SEO and AEO (Answer Engine Optimization) expert.
You specialize in optimizing content for both traditional search engines 
and AI-powered search tools like ChatGPT, Claude, Gemini, and Le Chat.

You will receive a JSON object representing a web page with the following structure:
{{
    "url": "the page URL",
    "markdown_content": "the page content in markdown",
    "structured_data": [...],
    "metadata": {{...}}
}}

Your task:
1. Improve the "markdown_content" for SEO: fix heading hierarchy, improve keyword usage,
   ensure the content is clear, well-structured, and answers common user questions directly.
2. Improve or complete the "structured_data": add or fix Schema.org JSON-LD blocks 
   (WebPage, Article, BreadcrumbList, FAQPage if relevant, etc.).
3. Improve the "metadata": ensure title (30-60 chars), meta description (50-160 chars),
   Open Graph tags, lang, robots, canonical, and a "summary" tag for LLM crawlers.
4. Add a "comment" field: a short paragraph (5-10 sentences) explaining the main flaws 
   found and what was improved, written for a non-technical audience.

CRITICAL INSTRUCTIONS FOR OUTPUT FORMAT:
- Return ONLY a valid JSON object.
- Do NOT wrap it in markdown code blocks (no ```json).
- Do NOT include any text before or after the JSON.
- In the "markdown_content" field, escape all special characters properly:
  * Use \\n for newlines (not actual newlines)
  * Use \\" for quotes inside strings
  * Use \\\\ for backslashes
- Ensure the entire response is parseable by Python's json.loads().

Here is the input data to optimize:
{json.dumps(cleaned_input, ensure_ascii=False, indent=2)}
"""

    message = self.client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16000,  # Increased to avoid truncation
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    raw_response = message.content[0].text
    print(f"\n✅ Response received ({len(raw_response)} chars)")
    print(f"Stop reason: {message.stop_reason}")

    # Clean common issues before parsing
    cleaned = raw_response.strip()
    
    # Remove markdown code fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()

    try:
        optimized_data = json.loads(cleaned)
        return optimized_data
    except json.JSONDecodeError as e:
        print(f"⚠️ First parse attempt failed: {e}")
        print(f"⚠️ Error at position {e.pos}, near: {repr(cleaned[max(0,e.pos-50):e.pos+50])}")
        
        # Try to extract JSON object more carefully
        # Find the outermost { ... } 
        start = cleaned.find('{')
        if start == -1:
            raise ValueError(f"No JSON object found in response:\n{cleaned[:500]}")
        
        # Count braces to find the matching closing brace
        depth = 0
        end = -1
        in_string = False
        escape_next = False
        
        for i, char in enumerate(cleaned[start:], start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
        
        if end == -1:
            raise ValueError("Could not find complete JSON object (possibly truncated response)")
        
        json_str = cleaned[start:end]
        
        try:
            optimized_data = json.loads(json_str)
            return optimized_data
        except json.JSONDecodeError as e2:
            print(f"⚠️ Second parse attempt failed at pos {e2.pos}: {repr(json_str[max(0,e2.pos-100):e2.pos+100])}")
            raise ValueError(f"Could not parse Claude response as JSON.\nError: {e2}\nRaw response snippet:\n{raw_response[max(0, e2.pos-200):e2.pos+200]}")



