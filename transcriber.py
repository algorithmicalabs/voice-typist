# transcriber.py
import assemblyai as aai

def transcribe_audio(api_key, filepath):
    """
    Transcribes the audio file at filepath using AssemblyAI.
    
    Args:
        api_key (str): The AssemblyAI API key.
        filepath (str): Path to the WAV audio file to transcribe.
        
    Returns:
        str: Transcribed text if successful.
        
    Raises:
        Exception: If transcription fails.
    """
    if not api_key:
        raise ValueError("AssemblyAI API key is missing. Please configure it in Settings.")
        
    # Configure API key
    aai.settings.api_key = api_key
    
    # Initialize the transcriber
    transcriber = aai.Transcriber()
    
    # Configure transcription options (enable auto-formatting and punctuation)
    config = aai.TranscriptionConfig(
        punctuate=True,
        format_text=True
    )
    
    try:
        # This uploads the file, polls AssemblyAI API, and blocks until finished
        transcript = transcriber.transcribe(filepath, config=config)
        
        # Check for transcription errors
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"AssemblyAI transcription error: {transcript.error}")
            
        return transcript.text
    except Exception as e:
        # Re-raise with a clean message
        raise Exception(f"Transcription failed: {str(e)}")
