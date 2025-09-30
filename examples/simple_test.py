"""Simple test of the workflow tool"""

import asyncio
from workflow.agents.orchestrator import Orchestrator


async def test_basic_workflow():
    """Test creating and running a simple workflow"""

    # Initialize orchestrator
    orch = Orchestrator()

    print("Testing workflow creation...")

    # Create a simple workflow
    workflow = await orch.teach_workflow(
        name="test-hello",
        description="Print hello world and current date",
        language="bash",
        interactive=False,
    )

    if workflow:
        print(f"✓ Created workflow: {workflow.name}")
        print(f"  Language: {workflow.language.value}")
        print(f"  Code length: {len(workflow.code)} chars")

    print("\nTesting workflow execution...")

    # Run the workflow
    success = await orch.run_workflow(
        name="test-hello",
        interactive=False,
    )

    if success:
        print("✓ Workflow executed successfully")
    else:
        print("✗ Workflow failed")

    print("\nTest completed!")


if __name__ == "__main__":
    asyncio.run(test_basic_workflow())
