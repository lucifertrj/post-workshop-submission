import asyncio
from intelligence.difficulty import default_estimator_registry
from intelligence.allocator import default_policy_registry
from pprint import pprint

async def main():
    estimator = default_estimator_registry.get_estimator("heuristic_estimator")
    allocator = default_policy_registry.get_policy("heuristic_allocator")
    
    query1 = "What is the capital of France?"
    query2 = "If John has 5 apples and eats 2, how many does he have? Compare this to Mary who has 10 apples."
    
    print(f"Query 1: {query1}")
    diff1 = await estimator.estimate(query1)
    alloc1 = await allocator.allocate(diff1)
    pprint(alloc1.model_dump())
    print("\n")
    
    print(f"Query 2: {query2}")
    diff2 = await estimator.estimate(query2)
    alloc2 = await allocator.allocate(diff2)
    pprint(alloc2.model_dump())

if __name__ == "__main__":
    asyncio.run(main())
