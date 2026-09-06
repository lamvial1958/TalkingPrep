"""Exceções específicas do pipeline TalkingPrep."""


class TalkingPrepError(Exception):
    """Erro genérico e esperado do pipeline (mensagem já formatada para o usuário)."""


class InvalidAudioError(TalkingPrepError):
    """Arquivo de áudio ausente, não-WAV, corrompido ou ilegível."""


class ExternalToolError(TalkingPrepError):
    """Falha ao invocar uma ferramenta externa (ffmpeg, demucs)."""


class DiskSpaceError(TalkingPrepError):
    """Falha de escrita em disco, possivelmente por falta de espaço."""
