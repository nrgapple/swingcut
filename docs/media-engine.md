# Deterministic media engine

Swingcut's media boundary uses `ffprobe` for normalized inventory and `ffmpeg` for every transformation. Commands are argument arrays, never shell strings. The engine hashes each staged source before transformation and again afterward; a changed source fails the operation and the output is removed.

## Cloud proxy profile

`silent-h264-480w-15fps-v1` is the only cloud-eligible profile:

- full source duration;
- H.264, `yuv420p`, 15 fps;
- display width capped at 480 pixels without upscaling;
- no audio or chapters; and
- input metadata discarded, with a post-encode check rejecting location, creation/date, device, make/model, title, or comment keys.

The resulting typed `ProxyArtifact` carries sanitizer verification and both source and proxy hashes. Original media is never an acceptable substitute. Broadening this profile requires explicit approval under the Relay charter.

## Photos output profile

`photos-h264-aac-sdr-v1` is a single-generation MP4 profile designed for QuickTime and Apple Photos compatibility:

- H.264 High Profile at CRF 18 using the slow preset and `yuv420p`;
- BT.709 SDR color signalling;
- AAC stereo at 48 kHz and 192 kbit/s;
- constant 30 fps and fast-start layout;
- source audio retained; silent source segments receive silence so concatenation remains deterministic; and
- no source metadata or chapters.

All-portrait plans select a 9:16 canvas capped at 1080×1920. Plans containing landscape or mixed orientations select 16:9, capped at 1920×1080. Canvas size is bounded by the largest source in the canvas orientation. Every segment is downscaled only when needed, centered, and letterboxed in black without cropping. The renderer trims directly from staged sources and performs no intermediate quality encode.

PQ (`smpte2084`) and HLG (`arib-std-b67`) inputs currently fail closed because merely relabelling HDR as SDR is unsafe; a tone-mapping profile must be validated on the approved private corpus before production support. The final verifier checks codec, pixel format, color signalling, canvas, frame rate, audio codec, planned duration, and full decodeability.

Routine tests generate private-free synthetic portrait/landscape, audio/silent, 24 fps, and 30000/1001 fps sources at test time. They verify sanitized proxies, mixed-orientation rendering, audible source-audio retention, silent-segment handling, output decoding, and unchanged source hashes.
