// Thin wrapper over the browser's EventSource for our typed SSE events.
//
// The backend emits three event types: "init", "iter", "done". This wrapper
// is GENERIC over the init/iter payload shapes so a single helper works for
// both deblur and denoise streams.

export type SSEHandlers<TInit, TIter> = {
  onInit?: (data: TInit) => void;
  onIter?: (data: TIter) => void;
  onDone?: () => void;
  onError?: (err: Event) => void;
};

export type SSEHandle = {
  close: () => void;
};

export function streamRun<TInit, TIter>(
  url: string,
  handlers: SSEHandlers<TInit, TIter>,
): SSEHandle {
  const es = new EventSource(url);

  es.addEventListener('init', (e) => {
    handlers.onInit?.(JSON.parse((e as MessageEvent).data));
  });
  es.addEventListener('iter', (e) => {
    handlers.onIter?.(JSON.parse((e as MessageEvent).data));
  });
  es.addEventListener('done', () => {
    handlers.onDone?.();
    es.close();
  });
  es.onerror = (e) => {
    handlers.onError?.(e);
    es.close();
  };

  return { close: () => es.close() };
}
