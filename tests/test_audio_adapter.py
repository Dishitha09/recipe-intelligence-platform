from services.ingestion.audio_adapter import AudioAdapter


def test_audio_adapter_returns_raw_record_for_existing_file(tmp_path):
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"")

    adapter = AudioAdapter(str(audio_path))
    records = adapter.extract()

    assert len(records) == 1
    assert records[0].source_type == "audio"
    assert records[0].metadata["filename"] == "sample.mp3"
    assert records[0].metadata["transcription_status"] == "transcription_missing"
    assert records[0].metadata["fallback_flags"] == ("transcription_missing",)


def test_audio_adapter_uses_transcript_sidecar(tmp_path):
    audio_path = tmp_path / "sample.mp3"
    transcript_path = tmp_path / "sample.txt"
    audio_path.write_bytes(b"")
    transcript_path.write_text(
        "Lemon Rice Audio\nIngredients:\n1 cup rice\nInstructions:\nMix rice.",
        encoding="utf-8",
    )

    adapter = AudioAdapter(
        str(audio_path),
        config={
            "transcript_path": str(transcript_path),
            "source_url": "file://sample.mp3",
        },
    )
    records = adapter.extract()

    assert records[0].raw_content["title"] == "Lemon Rice Audio"
    assert "1 cup rice" in records[0].raw_content["raw_text"]
    assert records[0].raw_content["source_url"] == "file://sample.mp3"
    assert records[0].metadata["transcription_status"] == "sidecar_file"


def test_audio_adapter_rejects_missing_file(tmp_path):
    adapter = AudioAdapter(str(tmp_path / "missing.mp3"))

    try:
        adapter.extract()
        raised = False
    except FileNotFoundError:
        raised = True

    assert raised is True
