import React, { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, RefreshCw, Minus, X, ToggleLeft, ToggleRight } from 'lucide-react';
import { useJarvisStore } from '../store/jarvisStore';

export const VisionWidget: React.FC = () => {
  const {
    isCameraActive,
    camFacingMode,
    camVisionMode,
    isCameraMinimized,
    setCameraActive,
    setCamFacingMode,
    setCamVisionMode,
    setCameraMinimized,
    registerCaptureFrameFn,
    addActivity,
  } = useJarvisStore();

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [dimensions] = useState({ width: 320, height: 240 });
  const [isLive, setIsLive] = useState(false);

  // Stop camera tracks
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsLive(false);
    addActivity('Camera feed stopped', 'status');
  }, [addActivity]);

  // Start camera feed
  const startCamera = useCallback(async (facing: 'user' | 'environment') => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      addActivity('Camera API not supported in this browser', 'error');
      return;
    }

    // Stop active stream first
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsLive(true);
      addActivity(`Camera stream started (${facing} mode)`, 'status');
    } catch (err: any) {
      console.error('Error starting camera:', err);
      addActivity(`Failed to access camera: ${err.message || err}`, 'error');
      setCameraActive(false);
    }
  }, [addActivity, setCameraActive]);

  // Monitor camera active state from store
  useEffect(() => {
    if (isCameraActive) {
      startCamera(camFacingMode);
    } else {
      stopCamera();
    }
    return () => {
      // Cleanup on unmount or state change
      if (!isCameraActive) {
        stopCamera();
      }
    };
  }, [isCameraActive, camFacingMode, startCamera, stopCamera]);

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Frame capture implementation
  const captureFrame = useCallback((): Promise<string | null> => {
    return new Promise((resolve) => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !streamRef.current || !canvas) {
        resolve(null);
        return;
      }

      const doCapture = () => {
        const w = video.videoWidth;
        const h = video.videoHeight;
        if (!w || !h || w < 64 || h < 64) {
          resolve(null);
          return;
        }

        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          resolve(null);
          return;
        }

        // Draw video frame to canvas
        ctx.drawImage(video, 0, 0, w, h);
        try {
          // Extract quality 0.9 jpeg base64
          const b64 = canvas.toDataURL('image/jpeg', 0.9).split(',')[1];
          resolve(b64);
        } catch (_) {
          resolve(null);
        }
      };

      // Check if video is loaded and playing
      if (video.readyState < 2) {
        const onReady = () => {
          video.removeEventListener('loadeddata', onReady);
          doCapture();
        };
        video.addEventListener('loadeddata', onReady);
        setTimeout(() => {
          video.removeEventListener('loadeddata', onReady);
          doCapture();
        }, 3000);
        return;
      }

      const w = video.videoWidth;
      const h = video.videoHeight;
      if (w && h && w >= 64 && h >= 64) {
        if (typeof video.requestVideoFrameCallback === 'function') {
          video.requestVideoFrameCallback(() => {
            doCapture();
          });
        } else {
          setTimeout(doCapture, 150);
        }
      } else {
        setTimeout(() => {
          const w2 = video.videoWidth || 0;
          const h2 = video.videoHeight || 0;
          if (w2 && h2 && w2 >= 64 && h2 >= 64) {
            doCapture();
          } else {
            resolve(null);
          }
        }, 300);
      }
    });
  }, []);

  // Register capture method to store
  useEffect(() => {
    if (isCameraActive) {
      registerCaptureFrameFn(captureFrame);
    } else {
      registerCaptureFrameFn(null);
    }
    return () => {
      registerCaptureFrameFn(null);
    };
  }, [isCameraActive, captureFrame, registerCaptureFrameFn]);

  if (!isCameraActive) return null;

  return (
    <AnimatePresence>
      <motion.div
        drag
        dragMomentum={false}
        dragListener={true}
        dragElastic={0}
        dragConstraints={{ left: 10, right: window.innerWidth - dimensions.width - 20, top: 10, bottom: window.innerHeight - (isCameraMinimized ? 50 : dimensions.height) - 20 }}
        initial={{ opacity: 0, scale: 0.9, x: window.innerWidth - dimensions.width - 40, y: 100 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        style={{ width: dimensions.width }}
        className="fixed z-40 bg-zinc-950/80 backdrop-blur-md border border-zinc-800/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col cursor-grab active:cursor-grabbing font-sans"
      >
        {/* Header (Drag Handle) */}
        <div className="flex items-center justify-between px-3 py-2 bg-zinc-900/50 border-b border-zinc-800/40 select-none">
          <div className="flex items-center gap-1.5 text-zinc-300 font-medium text-xs">
            <Camera size={13} className={isLive ? 'text-emerald-500 animate-pulse' : 'text-zinc-500'} />
            <span>Vision Pipeline</span>
          </div>

          <div className="flex items-center gap-2 pointer-events-auto">
            {/* Vision Auto Mode Toggle */}
            <div 
              className="flex items-center gap-1 cursor-pointer select-none text-[10px] text-zinc-400 mr-2"
              onClick={() => setCamVisionMode(!camVisionMode)}
              title="Vision Mode — auto capture frame on send"
            >
              <span>Auto-vision</span>
              {camVisionMode ? (
                <ToggleRight size={16} className="text-emerald-500" />
              ) : (
                <ToggleLeft size={16} className="text-zinc-500" />
              )}
            </div>

            {/* Flip Camera */}
            <button
              onClick={() => {
                const nextMode = camFacingMode === 'user' ? 'environment' : 'user';
                setCamFacingMode(nextMode);
              }}
              className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-colors"
              title="Flip camera"
            >
              <RefreshCw size={12} />
            </button>

            {/* Minimize */}
            <button
              onClick={() => setCameraMinimized(!isCameraMinimized)}
              className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-colors"
              title="Minimize panel"
            >
              <Minus size={12} />
            </button>

            {/* Close */}
            <button
              onClick={() => setCameraActive(false)}
              className="p-1 rounded text-zinc-400 hover:text-rose-400 hover:bg-rose-950/20 transition-colors"
              title="Close panel"
            >
              <X size={12} />
            </button>
          </div>
        </div>

        {/* Video / Canvas Body */}
        {!isCameraMinimized && (
          <div className="relative bg-black flex-1 flex flex-col justify-center select-none" style={{ height: dimensions.height - 35 }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover select-none pointer-events-none"
            />
            {/* Hidden canvas for capturing frames */}
            <canvas ref={canvasRef} className="hidden" />

            <div className="absolute bottom-2 left-2 px-1.5 py-0.5 rounded bg-zinc-950/60 backdrop-blur-sm border border-zinc-800/50 text-[9px] text-zinc-400 tracking-wider">
              {isLive ? 'LIVE FEED' : 'CONNECTING...'}
            </div>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
};
