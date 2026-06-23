import React, { useEffect, useState } from 'react';
import { Loader2, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import { useJarvisStore } from '../store/jarvisStore';

interface TaskCardProps {
  taskId: string;
  type: string;
  label?: string;
}

export const TaskCard: React.FC<TaskCardProps> = ({ taskId, type, label }) => {
  const [status, setStatus] = useState<'pending' | 'completed' | 'failed'>('pending');
  const [errorMsg, setErrorMsg] = useState<string>('');
  const { addActivity } = useJarvisStore();

  const getTaskLabel = () => {
    if (label) return label;
    if (type === 'generate image') return 'Image Generation';
    if (type === 'content') return 'Content Writing';
    return type;
  };

  useEffect(() => {
    let pollCount = 0;
    const maxPolls = 120; // 3 minutes timeout

    const poll = async () => {
      pollCount++;
      if (pollCount > maxPolls) {
        setStatus('failed');
        setErrorMsg('Task execution timed out.');
        addActivity(`Task ${taskId} timed out.`, 'error');
        return;
      }

      try {
        const res = await fetch(`/tasks/${encodeURIComponent(taskId)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.status === 'completed') {
          setStatus('completed');
          addActivity(`Task ${getTaskLabel()} (${taskId}) completed successfully!`, 'execution');
          
          // Auto open result tab (standard legacy behavior)
          try {
            window.open(`/app/viewer.html?task_id=${taskId}`, '_blank');
          } catch (_) {
            console.warn('Popup blocked, link is available');
          }
        } else if (data.status === 'failed') {
          setStatus('failed');
          setErrorMsg(data.error || 'Execution failed');
          addActivity(`Task ${getTaskLabel()} (${taskId}) failed: ${data.error || 'Execution error'}`, 'error');
        } else {
          // Continue polling
          setTimeout(poll, 1500);
        }
      } catch (err: any) {
        console.error('Error polling background task:', err);
        // Continue polling despite network hiccups
        setTimeout(poll, 1500);
      }
    };

    // Delay first poll slightly
    const timer = setTimeout(poll, 1000);
    return () => clearTimeout(timer);
  }, [taskId, type, label, addActivity]);

  return (
    <div className="my-3 p-4 rounded-xl border bg-zinc-900/40 border-zinc-800/80 backdrop-blur-sm flex items-center justify-between text-white font-sans text-xs">
      <div className="flex items-center gap-3">
        {status === 'pending' && (
          <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
        )}
        {status === 'completed' && (
          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
        )}
        {status === 'failed' && (
          <AlertCircle className="w-5 h-5 text-rose-500" />
        )}

        <div className="flex flex-col">
          <span className="font-semibold text-zinc-100 uppercase tracking-wide text-[10px]">
            {getTaskLabel()}
          </span>
          <span className="text-[10px] text-zinc-400 font-mono">
            {status === 'pending' && 'Executing task pipeline...'}
            {status === 'completed' && 'Completed!'}
            {status === 'failed' && (errorMsg || 'Pipeline failed')}
          </span>
        </div>
      </div>

      {status === 'completed' && (
        <a
          href={`/app/viewer.html?task_id=${taskId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all font-medium text-[11px]"
        >
          <span>Open Results</span>
          <ExternalLink size={12} />
        </a>
      )}
    </div>
  );
};
