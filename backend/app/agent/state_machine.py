from app.schemas.agent_state import AgentMessage, AgentState


def _copy(state: AgentState) -> AgentState:
    return state.model_copy(deep=True)


def append_user_message(state: AgentState, content: str) -> AgentState:
    if not content.strip():
        raise ValueError("消息内容不能为空")
    new_state = _copy(state)
    new_state.messages.append(AgentMessage(role="user", content=content.strip()))
    new_state.conversation_round += 1
    return new_state


def append_assistant_message(state: AgentState, content: str) -> AgentState:
    if not content.strip():
        raise ValueError("消息内容不能为空")
    new_state = _copy(state)
    new_state.messages.append(AgentMessage(role="assistant", content=content.strip()))
    return new_state


def should_stop_conversation(state: AgentState) -> bool:
    return state.conversation_round >= state.max_rounds


def register_ai_failure(state: AgentState, error_message: str) -> AgentState:
    new_state = _copy(state)
    new_state.ai_failure_count += 1
    new_state.validation_errors.append(error_message)
    if new_state.ai_failure_count >= new_state.max_ai_failures:
        new_state.status = "fallback_questionnaire"
    return new_state


def decide_branch_from_q5(state: AgentState) -> AgentState:
    new_state = _copy(state)
    selected = new_state.answers.get("Q5", [])
    if not selected:
        return new_state
    if len(selected) != 1:
        new_state.validation_errors.append(f"Q5 期望 1 个选项，实际 {len(selected)} 个")
        new_state.branch = None
        return new_state
    option = selected[0]
    if option in ("A", "B", "C"):
        new_state.branch = "experienced"
    elif option == "D":
        new_state.branch = "inexperienced"
    else:
        new_state.validation_errors.append(f"Q5 无效选项: {option}")
        new_state.branch = None
    return new_state


def is_ready_to_score(state: AgentState) -> bool:
    if state.status != "active":
        return False
    if state.branch != "experienced":
        return False
    if len(state.validation_errors) > 0:
        return False
    selected = state.answers.get("Q5", [])
    if selected != ["A"] and selected != ["B"] and selected != ["C"]:
        return False
    if len(state.answers) < 8:
        return False
    return True


def trim_message_history(state: AgentState, max_messages: int = 12) -> AgentState:
    if len(state.messages) <= max_messages:
        return _copy(state)
    new_state = _copy(state)
    new_state.messages = new_state.messages[-max_messages:]
    return new_state
