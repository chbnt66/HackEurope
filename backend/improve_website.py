import anthropic
import json
import re
from dotenv import load_dotenv
import os

load_dotenv()

def optimize_seo_with_claude(result_data: dict) -> dict:
    """
    Takes a result_data dict with url, markdown_content, structured_data, metadata
    and returns the same structure optimized for SEO/AEO, with a 'comment' field.
    """

    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API"))  # uses ANTHROPIC_API_KEY env variable

    prompt = f"""
You are an SEO and AEO (Answer Engine Optimization) expert.
You specialize in optimizing content for both traditional search engines 
and AI-powered search tools like ChatGPT, Claude, Gemini, and Le Chat.

You will receive a JSON object representing a web page with the following structure:
{{
    "url": "the page URL",
    "markdown_content": "the page content in markdown",
    "structured_data": [...],  // existing Schema.org / JSON-LD structured data
    "metadata": {{...}}        // existing HTML metadata (title, description, og tags, etc.)
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

Return ONLY a valid JSON object with this exact structure:
{{
    "url": "...",
    "markdown_content": "...",
    "structured_data": [...],
    "metadata": {{...}},
    "comment": "..."
}}

Do not include any explanation outside the JSON. Do not wrap it in markdown code blocks.

Here is the input data to optimize:
{json.dumps(result_data, ensure_ascii=False, indent=2)}
"""
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    raw_response = message.content[0].text
    print("\n✅ Stream complete.")

    

   # raw_response = message.content[0].text

    try:
        optimized_data = json.loads(raw_response)
    except json.JSONDecodeError:
        # Fallback: try to extract JSON if Claude added any surrounding text
        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if match:
            optimized_data = json.loads(match.group())
        else:
            raise ValueError(f"Claude returned non-JSON response:\n{raw_response}")

    return optimized_data


html_page =  [{
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebPage",
        "@id": "https://4ipgroup.com/",
        "url": "https://4ipgroup.com/",
        "name": "4IP Group Home Page - 4IP Group",
        "isPartOf": {
          "@id": "https://4ipgroup.com/#website"
        },
        "about": {
          "@id": "https://4ipgroup.com/#organization"
        },
        "primaryImageOfPage": {
          "@id": "https://4ipgroup.com/#primaryimage"
        },
        "image": {
          "@id": "https://4ipgroup.com/#primaryimage"
        },
        "thumbnailUrl": "https://4ipgroup.com/wp-content/uploads/2024/06/coins-stacked-dirt-with-plants2.webp",
        "datePublished": "2022-01-17T13:01:14+00:00",
        "dateModified": "2026-02-09T17:41:28+00:00",
        "description": "4IP Group is a leading impact investing and ESG advisory firm based in Geneva, offering strategic advisory, accredited SDG impact training, capital raising and investment matchmaking services that help enterprises and investors achieve sustainable growth across emerging and frontier markets.",
        "breadcrumb": {
          "@id": "https://4ipgroup.com/#breadcrumb"
        },
        "inLanguage": "en-US",
        "potentialAction": [
          {
            "@type": "ReadAction",
            "target": [
              "https://4ipgroup.com/"
            ]
          }
        ]
      },
      {
        "@type": "ImageObject",
        "inLanguage": "en-US",
        "@id": "https://4ipgroup.com/#primaryimage",
        "url": "https://4ipgroup.com/wp-content/uploads/2024/06/coins-stacked-dirt-with-plants2.webp", 
        "contentUrl": "https://4ipgroup.com/wp-content/uploads/2024/06/coins-stacked-dirt-with-plants2.webp",
        "width": 1200,
        "height": 800,
        "caption": "4IP Group Tanzania"
      },
      {
        "@type": "BreadcrumbList",
        "@id": "https://4ipgroup.com/#breadcrumb",
        "itemListElement": [
          {
            "@type": "ListItem",
            "position": 1,
            "name": "Home"
          }
        ]
      },
      {
        "@type": "WebSite",
        "@id": "https://4ipgroup.com/#website",
        "url": "https://4ipgroup.com/",
        "name": "4IP Group",
        "description": "Building Bridges in Investment",
        "publisher": {
          "@id": "https://4ipgroup.com/#organization"
        },
        "potentialAction": [
          {
            "@type": "SearchAction",
            "target": {
              "@type": "EntryPoint",
              "urlTemplate": "https://4ipgroup.com/?s={search_term_string}"
            },
            "query-input": {
              "@type": "PropertyValueSpecification",
              "valueRequired": True,
              "valueName": "search_term_string"
            }
          }
        ],
        "inLanguage": "en-US"
      },
      {
        "@type": "Organization",
        "@id": "https://4ipgroup.com/#organization",
        "name": "Independent Infrastructure Impact Investing Partners (4IP Group)",
        "url": "https://4ipgroup.com/",
        "logo": {
          "@type": "ImageObject",
          "inLanguage": "en-US",
          "@id": "https://4ipgroup.com/#/schema/logo/image/",
          "url": "https://4ipgroup.com/wp-content/uploads/2024/06/4ip-logo-transparent.png",
          "contentUrl": "https://4ipgroup.com/wp-content/uploads/2024/06/4ip-logo-transparent.png",
          "width": 1000,
          "height": 519,
          "caption": "Independent Infrastructure Impact Investing Partners (4IP Group)"
        },
        "image": {
          "@id": "https://4ipgroup.com/#/schema/logo/image/"
        },
        "sameAs": [
          "https://x.com/4ipGroup3918",
          "https://www.linkedin.com/company/4ip-infrastructure-and-impact-investing/"
        ]
      }
    ]
  }]

result_data = {
    "url": "https://4ipgroup.com/",
    "markdown_content": "",
    "structured_data": html_page,  # ← wrap in a list
    "metadata": {}
}



opti_data = optimize_seo_with_claude(result_data = html_page )

print(f"opti_data.keys() = {opti_data.keys()}\n\n\n")

if "comment" in opti_data.keys() : 
    print(f"comment : {opti_data['comment']}")

