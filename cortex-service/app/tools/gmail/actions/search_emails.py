"""Sub-action handler for searching emails."""

from ..schemas import GmailToolArgs, EvidenceItem
from ..content.mime_parser import extract_body_and_headers
from ..content.sanitizer import HTMLSanitizer
from ..content.normalizer import ContentNormalizer
from ..transport.retry import with_backoff

_sanitizer = HTMLSanitizer()
_normalizer = ContentNormalizer()

async def run(args: GmailToolArgs, client, compiler, project_id: str) -> list[EvidenceItem]:
    # 1. Compile Natural Language to Gmail Query
    compiled_query = await compiler.compile(args.query or "", project_id=project_id)
    gmail_query = compiled_query.to_query_string()

    ## for debugging purpose only
    print(f"\n   -> [GMAIL COMPILER] Executing API Query: '{gmail_query}'")
    # 2. Fetch Message References
    message_refs = await with_backoff(
        lambda: client.list_messages(query=gmail_query, max_results=args.max_results)
    )
    
    items: list[EvidenceItem] = []
    
    # 3. Process Each Message
    for ref in message_refs:
        full_msg = await with_backoff(lambda ref=ref: client.get_message(ref["id"]))
        headers, raw_body, is_html = extract_body_and_headers(full_msg)
        
        body = _sanitizer.strip(raw_body) if is_html else raw_body
        body = _normalizer.normalize(body)
        
        # --- FIX: Remove \n\n and replace with a single space or separator ---
        # This prevents RecursiveCharacterTextSplitter from severing the body from the header
        content = (
            f"From: {headers.get('From')} | "
            f"Subject: {headers.get('Subject')} | "
            f"Date: {headers.get('Date')} -- "
            f"BODY: {body}"
        )
        # Ensure we don't have stray double newlines in the body that cause splits
        content = content.replace("\n\n", " ")
        
        items.append(EvidenceItem(
            content=content,
            source=f"Gmail (ID: {ref['id']})",
            score=min(1.0, compiled_query.overall_confidence),
            metadata={"thread_id": full_msg.get("threadId"), "query_used": gmail_query},
        ))
        
    return items