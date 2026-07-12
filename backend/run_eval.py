import asyncio, httpx

async def main():
    async with httpx.AsyncClient() as c:
        r = await c.post('http://localhost:8000/auth/dev-login', json={'name':'eval','role':'consultant'})
        token = r.json()['access_token']
        r = await c.get('http://localhost:8000/knowledge/eval', headers={'Authorization': f'Bearer {token}'}, timeout=120)
        s = r.json()['summary']
        print(f'=== RAG Eval ===')
        print(f'Queries: {s["total_queries"]}')
        print(f'Recall@3:    {s["recall_at_k"]:.2%}')
        print(f'Precision@3: {s["precision_at_k"]:.2%}')
        print(f'MRR:         {s["mrr"]:.4f}')
        print(f'Hit Rate@3:  {s["hit_rate_at_k"]:.2%}')

asyncio.run(main())
