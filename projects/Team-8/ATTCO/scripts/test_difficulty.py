import asyncio
from intelligence.difficulty import default_estimator_registry
from pprint import pprint

async def main():
    estimator = default_estimator_registry.get_estimator("heuristic_estimator")
    query1 = "What is the capital of France?"
    query2 = "If John has 5 apples and eats 2, how many does he have? Compare this to Mary who has 10 apples."
    
    print(f"Query 1: {query1}")
    res1 = await estimator.estimate(query1)
    pprint(res1.model_dump())
    print("\n")
    
    print(f"Query 2: {query2}")
    res2 = await estimator.estimate(query2)
    pprint(res2.model_dump())

if __name__ == "__main__":
    asyncio.run(main())
