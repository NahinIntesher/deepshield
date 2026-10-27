import 'dart:async';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../core/api.dart';
import '../core/session.dart';
import 'kit.dart';

class MediaPlayer extends StatefulWidget {
  final String url;
  final bool image;
  const MediaPlayer(this.url, {super.key, this.image = false});
  @override
  State<MediaPlayer> createState() => _MediaPlayerState();
}

class _MediaPlayerState extends State<MediaPlayer> with WidgetsBindingObserver {
  VideoPlayerController? controller;
  String? error;
  bool starting = false;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) controller?.pause();
  }

  Future<void> start() async {
    setState(() {
      starting = true;
      error = null;
    });
    try {
      final app = AppScope.of(context);
      final c = VideoPlayerController.networkUrl(
        Uri.parse(app.api.media(widget.url)),
        httpHeaders: app.api.headers,
      );
      controller = c;
      await c.initialize();
      if (!mounted) {
        await c.dispose();
        return;
      }
      c.addListener(update);
      await c.play();
    } catch (e) {
      if (mounted) setState(() => error = Api.errorText(e));
    } finally {
      if (mounted) setState(() => starting = false);
    }
  }

  void update() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    controller?.removeListener(update);
    controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    if (widget.image) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Image.network(
          app.api.media(widget.url),
          headers: app.api.headers,
          fit: BoxFit.contain,
          loadingBuilder: (_, child, loading) => loading == null
              ? child
              : const Center(child: CircularProgressIndicator()),
          errorBuilder: (_, e, s) => Notice(
            app.t('Could not load this image.', 'ছবিটি লোড হয়নি।'),
            error: true,
          ),
        ),
      );
    }
    final c = controller;
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: AspectRatio(
            aspectRatio: c?.value.isInitialized == true
                ? c!.value.aspectRatio
                : 16 / 9,
            child: ColoredBox(
              color: const Color(0xff101312),
              child: c?.value.isInitialized == true
                  ? VideoPlayer(c!)
                  : Center(
                      child: starting
                          ? const CircularProgressIndicator()
                          : IconButton.filled(
                              onPressed: start,
                              tooltip: app.t('Play video', 'ভিডিও চালান'),
                              icon: const Icon(Icons.play_arrow, size: 36),
                            ),
                    ),
            ),
          ),
        ),
        if (error != null) Notice(error!, error: true),
        if (c?.value.isInitialized == true) ...[
          VideoProgressIndicator(
            c!,
            allowScrubbing: true,
            padding: const EdgeInsets.symmetric(vertical: 12),
          ),
          Row(
            children: [
              IconButton(
                onPressed: () => c.value.isPlaying ? c.pause() : c.play(),
                tooltip: app.t(c.value.isPlaying ? 'Pause' : 'Play'),
                icon: Icon(c.value.isPlaying ? Icons.pause : Icons.play_arrow),
              ),
              Text(
                '${c.value.position.inSeconds}s / ${c.value.duration.inSeconds}s',
              ),
              const Spacer(),
              IconButton(
                onPressed: () => c.setVolume(c.value.volume > 0 ? 0 : 1),
                tooltip: app.t('Mute or unmute', 'সাউন্ড চালু বা বন্ধ করুন'),
                icon: Icon(
                  c.value.volume > 0
                      ? Icons.volume_up_outlined
                      : Icons.volume_off_outlined,
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
