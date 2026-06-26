"""Single-sourced torch `weights_only` allowlist for pyannote checkpoints.

torch 2.6+ flipped `torch.load`'s default to `weights_only=True`. Loading
pyannote's `segmentation-3.0` checkpoint (the VAD engine) hits that flip:
`Model.from_pretrained(...)` / the VoiceActivityDetection pipeline load the
gated segmentation checkpoint via lightning's `pl_load` -> `torch.load`.

pyannote doesn't pass `weights_only=False`, so the safe unpickler rejects the
non-tensor classes (omegaconf configs, pyannote task specs, stdlib containers)
baked into the checkpoint. We can't downgrade torch below the flip, so — as
pyannote's own error message recommends — we allowlist exactly the globals the
checkpoint needs instead of blanket-disabling `weights_only`.

`torch.serialization.add_safe_globals(...)` is process-global and idempotent,
so a single application before the first pyannote load covers every path. We
hoist it here so the list is single-sourced (AGENTS.md DRY rule). The set was
discovered empirically — torch names one missing global at a time — against
`pyannote.audio>=3.3.2,<4` on `torch>=2.x`.

faster-whisper (CTranslate2) does NOT use `torch.load` for its model weights,
so this allowlist is pyannote-only; it's a no-op for the transcription path.

Heavy imports stay lazy (inside the function) per the engine's lazy-import
invariant, so importing this module is free.
"""


def allowlist_pyannote_globals() -> None:
    """Allowlist the globals pyannote's checkpoints unpickle under torch 2.6+.

    Idempotent and process-global. Call before any `torch.load`-backed pyannote
    checkpoint load (the segmentation / VAD pipeline).
    """
    import collections
    import typing

    import torch  # type: ignore
    from omegaconf.base import ContainerMetadata, Metadata  # type: ignore
    from omegaconf.listconfig import ListConfig  # type: ignore
    from omegaconf.nodes import AnyNode  # type: ignore
    from pyannote.audio.core.model import Introspection  # type: ignore
    from pyannote.audio.core.task import (  # type: ignore
        Problem,
        Resolution,
        Specifications,
    )

    torch.serialization.add_safe_globals(
        [
            # torch / pyannote task metadata
            torch.torch_version.TorchVersion,
            Specifications,
            Problem,
            Resolution,
            Introspection,
            # omegaconf-pickled hyperparameter configs
            ListConfig,
            ContainerMetadata,
            Metadata,
            AnyNode,
            # stdlib containers / scalars referenced by those configs
            typing.Any,
            collections.defaultdict,
            list,
            dict,
            int,
        ]
    )
