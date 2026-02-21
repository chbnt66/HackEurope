def markdown_to_html(markdown, title="", description="", is_new=False):
    import re

    # Convert basic markdown to HTML
    def convert_md(text):
        # Headers
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Links
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'<span class="link">\1</span>', text)
        # Images (skip SVG placeholders)
        text = re.sub(r'!\[.*?\]\(data:image/svg\+xml.*?\)', '', text)
        # Paragraphs
        lines = text.split('\n')
        result = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('<h') or line.startswith('<ul') or line.startswith('<li'):
                result.append(line)
            else:
                result.append(f'<p>{line}</p>')
        return '\n'.join(result)

    badge = '<div class="badge">✨ SEO Optimized</div>' if is_new else ''
    accent = "#00C896" if is_new else "#6c757d"
    tag_bg = "#e6fff8" if is_new else "#f8f9fa"

    return f"""
    <html>
    <head>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}

            body {{
                font-family: 'DM Sans', sans-serif;
                font-weight: 300;
                background: #f7f5f0;
                color: #1a1a2e;
                font-size: 13px;
                line-height: 1.7;
            }}

            mark {{
                background: #fff9c4;
                color: #1a1a2e;
                padding: 1px 3px;
                border-radius: 3px;
                font-style: normal;
                }}

            .site-header {{
                background: #1a1a2e;
                color: white;
                padding: 16px 20px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                position: sticky;
                top: 0;
                z-index: 10;
                border-bottom: 3px solid {accent};
            }}

            .site-header .site-title {{
                font-family: 'Playfair Display', serif;
                font-size: 1.1em;
                letter-spacing: 0.5px;
            }}

            .badge {{
                background: {accent};
                color: white;
                font-size: 0.7em;
                font-weight: 500;
                padding: 3px 10px;
                border-radius: 20px;
                letter-spacing: 0.5px;
            }}

            .meta-bar {{
                background: {tag_bg};
                border-left: 3px solid {accent};
                padding: 12px 16px;
                margin: 16px;
                border-radius: 0 8px 8px 0;
                font-size: 0.78em;
                color: #444;
            }}

            .meta-bar strong {{
                color: {accent};
                font-weight: 500;
            }}

            .meta-bar .desc {{
                margin-top: 4px;
                color: #666;
                font-style: italic;
            }}

            .content {{
                padding: 8px 20px 40px;
            }}

            h1 {{
                font-family: 'Playfair Display', serif;
                font-size: 1.5em;
                color: #1a1a2e;
                margin: 20px 0 8px;
                line-height: 1.3;
                border-bottom: 2px solid {accent};
                padding-bottom: 6px;
            }}

            h2 {{
                font-family: 'Playfair Display', serif;
                font-size: 1.2em;
                color: #2d2d44;
                margin: 18px 0 6px;
            }}

            h3 {{
                font-size: 1em;
                font-weight: 500;
                color: {accent};
                margin: 14px 0 4px;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                font-size: 0.85em;
            }}

            p {{
                margin: 6px 0;
                color: #333;
                font-size: 0.88em;
            }}

            strong {{
                font-weight: 500;
                color: #1a1a2e;
            }}

            .link {{
                color: {accent};
                text-decoration: underline;
                cursor: pointer;
                font-weight: 400;
            }}

            

            /* Highlight new sections if is_new */
            {"h2, h3 { position: relative; } h2::after { content: ''; position: absolute; left: -16px; top: 0; bottom: 0; width: 3px; background: " + accent + "; border-radius: 2px; }" if is_new else ""}
        </style>
    </head>
    <body>
        <div class="site-header">
            <span class="site-title">{title or 'Website Preview'}</span>
            {badge}
        </div>

        <div class="meta-bar">
            <strong>Meta description:</strong>
            <div class="desc">{description or 'No description provided'}</div>
        </div>

        <div class="content">
            {convert_md(markdown)}
        </div>
    </body>
    </html>
    """