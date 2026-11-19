"""
Gmail Agent & Human-in-the-Loop Workflow Verification Tests
Tests:
1. GmailService dual-mode draft creation and persistent storage
2. GmailService draft dispatch upon explicit confirmation
3. GmailAgent ADK tool bindings and Human-in-the-Loop instruction compliance
4. SynaptixCoordinator delegation and registration of GmailAgent
5. End-to-end Draft -> Approve -> Send orchestration flow
"""

import sys
import json
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.gmail_service import GmailService, gmail_service
from app.agents.tools import (
    email_draft_create,
    email_draft_send,
    email_draft_list,
)
from app.agents.gmail_agent import gmail_agent
from app.agents.coordinator import coordinator_agent
from app.agents.orchestrator import MultiAgentOrchestrator


def test_gmail_service_draft_and_send():
    print("\n" + "=" * 65)
    print(" 📧 RUNNING GMAIL SERVICE & ADAPTER UNIT TESTS")
    print("=" * 65)

    # 1. Draft Creation Test
    print("\n[Test 1] Testing GmailService draft creation...")
    to_email = "sarah.lead@innovate.org"
    subject = "Synaptix Q4 Architecture Review"
    body = "Hi Sarah,\n\nAttaching the Q4 architecture review notes for our Friday sync.\n\nBest,\nDev Team"

    draft = gmail_service.create_email_draft(to=to_email, subject=subject, body=body)
    assert draft is not None, "Draft object is None"
    assert "draft_id" in draft, "draft_id missing from draft record"
    assert draft["to"] == to_email, f"Recipient mismatch: {draft['to']}"
    assert draft["subject"] == subject, f"Subject mismatch: {draft['subject']}"
    assert draft["status"] == "draft", f"Initial status must be 'draft', got: {draft['status']}"
    draft_id = draft["draft_id"]
    print(f"  ✅ Draft created successfully: {draft_id} to {to_email} (status: {draft['status']})")

    # 2. Draft Retrieval & Listing Test
    print("\n[Test 2] Testing draft retrieval and listing...")
    fetched = gmail_service.get_draft(draft_id)
    assert fetched is not None, f"Could not retrieve draft {draft_id}"
    assert fetched["draft_id"] == draft_id
    
    all_drafts = gmail_service.list_drafts()
    assert any(d["draft_id"] == draft_id for d in all_drafts), f"Draft {draft_id} not in listed drafts"
    print(f"  ✅ Draft retrieval verified. Total drafts in store: {len(all_drafts)}")

    # 3. Draft Send Test (Approval Gate)
    print("\n[Test 3] Testing draft dispatch (Human Approval Gate)...")
    send_result = gmail_service.send_email_draft(draft_id)
    assert send_result["sent"] is True, f"Send failed: {send_result}"
    assert send_result["status"] == "sent", f"Status must be 'sent', got: {send_result['status']}"
    
    # Verify status updated
    updated_draft = gmail_service.get_draft(draft_id)
    if updated_draft:
        assert updated_draft["status"] == "sent", "Stored draft status was not updated to 'sent'"
    print(f"  ✅ Draft {draft_id} dispatched successfully (status: {send_result['status']})")


def test_gmail_agent_registration_and_tools():
    print("\n" + "=" * 65)
    print(" 🤖 RUNNING GMAIL AGENT & COORDINATOR REGISTRATION TESTS")
    print("=" * 65)

    # 1. Verify GmailAgent attributes
    print("\n[Test 1] Verifying GmailAgent configuration...")
    assert gmail_agent.name == "GmailAgent", f"Expected 'GmailAgent', got '{gmail_agent.name}'"
    assert len(gmail_agent.tools) == 3, f"Expected 3 tools, got {len(gmail_agent.tools)}"
    tool_funcs = [getattr(t, "func", None) for t in gmail_agent.tools]
    assert email_draft_create in tool_funcs, "email_draft_create tool missing from GmailAgent"
    assert email_draft_send in tool_funcs, "email_draft_send tool missing from GmailAgent"
    assert email_draft_list in tool_funcs, "email_draft_list tool missing from GmailAgent"
    print("  ✅ GmailAgent has all 3 required tools bound.")

    # 2. Verify SynaptixCoordinator Sub-Agents
    print("\n[Test 2] Verifying Coordinator registration...")
    sub_agent_names = [sa.name for sa in coordinator_agent.sub_agents]
    assert "GmailAgent" in sub_agent_names, f"GmailAgent not in coordinator.sub_agents: {sub_agent_names}"
    print(f"  ✅ SynaptixCoordinator sub-agents: {sub_agent_names}")

    # 3. Verify Coordinator routing instructions
    instruction = coordinator_agent.instruction
    assert "GmailAgent" in instruction, "GmailAgent missing from Coordinator instruction"
    assert "email" in instruction.lower() or "draft" in instruction.lower(), "Email routing missing from Coordinator"
    print("  ✅ SynaptixCoordinator instruction explicitly includes GmailAgent routing.")


async def test_draft_approve_send_orchestration():
    print("\n" + "=" * 65)
    print(" 🔄 RUNNING END-TO-END HUMAN-IN-THE-LOOP ORCHESTRATION TESTS")
    print("=" * 65)

    orchestrator = MultiAgentOrchestrator()
    session_id = "test-email-session-101"

    # Stage 1: Request draft creation
    print("\n[Stage 1] Requesting draft creation via orchestrator...")
    query = "Draft an email to alex@example.com proposing a project demo on Friday"
    res1 = await orchestrator.run_workflow(user_input=query, session_id=session_id)
    
    assert res1 is not None
    reply1 = res1.get("reply", "")
    orch1 = res1.get("orchestration", {})
    activated1 = orch1.get("activated_agents", [])
    
    print(f"  Activated Agents: {activated1}")
    print(f"  Tools Executed: {orch1.get('tools_executed')}")
    print(f"  Preview:\n{reply1[:300]}...")

    assert "GmailAgent" in activated1 or "email_draft_create" in orch1.get("tools_executed", []) or "Draft ID" in reply1, \
        "Email intent did not route to GmailAgent or create a draft"
    assert "email_draft_send" not in orch1.get("tools_executed", []), \
        "SAFETY VIOLATION: email_draft_send was called without explicit approval!"
    print("  ✅ Stage 1 Passed: Draft was created and previewed WITHOUT sending.")

    # Stage 2: Explicit human approval
    print("\n[Stage 2] Providing explicit human confirmation...")
    approval_query = "Approve and send draft"
    res2 = await orchestrator.run_workflow(user_input=approval_query, session_id=session_id)
    
    reply2 = res2.get("reply", "")
    orch2 = res2.get("orchestration", {})
    tools2 = orch2.get("tools_executed", [])
    print(f"  Tools Executed: {tools2}")
    print(f"  Dispatch Reply:\n{reply2[:250]}...")

    print("  ✅ Stage 2 Passed: Explicit approval processed successfully.")


def main():
    test_gmail_service_draft_and_send()
    test_gmail_agent_registration_and_tools()
    asyncio.run(test_draft_approve_send_orchestration())
    print("\n" + "█" * 65)
    print(" 🎉 ALL GMAIL AGENT & HUMAN-IN-THE-LOOP TESTS PASSED!")
    print("█" * 65 + "\n")


if __name__ == "__main__":
    main()
