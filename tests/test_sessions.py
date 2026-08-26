from app.sessions import SessionStore


def test_session_turns_and_delete():
    store = SessionStore()
    session = store.create()
    store.append_turn(session.id, "질문", "답변")
    assert len(store.get(session.id).turns) == 2
    assert store.delete(session.id).id == session.id
    assert store.get(session.id) is None


def test_history_is_bounded():
    store = SessionStore(max_turns=2)
    session = store.create()
    for index in range(4):
        store.append_turn(session.id, f"q{index}", f"a{index}")
    assert [item["content"] for item in store.get(session.id).turns] == ["q2", "a2", "q3", "a3"]
