from services.ingestion.audio_adapter import AudioAdapter


adapter = AudioAdapter(

    "sample_audio.mp3"

)


print(

    adapter.extract()

)


print(

    adapter.transform()

)


print(

    adapter.load()

)