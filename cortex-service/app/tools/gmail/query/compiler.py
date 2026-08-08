# app/tools/gmail/query/compiler.py

from datetime import datetime
from .operators import CompiledGmailQuery, GmailQueryFragment, GmailOperator
from .rules import RelativeWindowResolver
from .llm_fallback import LLMQueryFallback

class NLQueryCompiler:
    def __init__(self, llm_fallback: LLMQueryFallback, reference_datetime_provider):
        self._llm_fallback = llm_fallback
        self._now = reference_datetime_provider
        self._resolvers = [RelativeWindowResolver()]

    async def compile(self, nl_query: str, project_id: str) -> CompiledGmailQuery:
        ref_time = self._now()
        compiled = CompiledGmailQuery()
        
        # 1. Try Deterministic Rules First
        for resolver in self._resolvers:
            fragments = resolver.resolve(nl_query, ref_time)
            if fragments:
                compiled.fragments.extend(fragments)
                
        if compiled.fragments:
            compiled.overall_confidence = sum(f.confidence for f in compiled.fragments) / len(compiled.fragments)
            
        # 2. Check threshold and fallback to LLM
        if not compiled.fragments or compiled.overall_confidence < 0.75:
            llm_output = await self._llm_fallback.translate(nl_query)
            
            # --- FIX: Helper to wrap strings with spaces in quotes ---
            def quote_if_needed(val: str) -> str:
                return f'"{val}"' if ' ' in val else val

            # --- FIX: Map ALL fields, including Subject, safely ---
            if llm_output.after:
                compiled.fragments.append(GmailQueryFragment(GmailOperator.AFTER, llm_output.after, 0.8, "llm"))
            if llm_output.before:
                compiled.fragments.append(GmailQueryFragment(GmailOperator.BEFORE, llm_output.before, 0.8, "llm"))
            if llm_output.from_:
                compiled.fragments.append(GmailQueryFragment(GmailOperator.FROM, quote_if_needed(llm_output.from_), 0.8, "llm"))
            if llm_output.subject:
                compiled.fragments.append(GmailQueryFragment(GmailOperator.SUBJECT, quote_if_needed(llm_output.subject), 0.8, "llm"))
            if llm_output.is_unread:
                compiled.fragments.append(GmailQueryFragment(GmailOperator.IS, "unread", 0.9, "llm"))
                
            compiled.raw_keywords.extend(llm_output.residual_keywords)
            compiled.overall_confidence = max(compiled.overall_confidence, 0.8) 

        # If absolutely nothing was parsed, just use the raw query as a fallback keyword search
        if not compiled.fragments and not compiled.raw_keywords:
            compiled.raw_keywords.append(nl_query)

        return compiled