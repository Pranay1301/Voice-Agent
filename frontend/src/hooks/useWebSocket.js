import { useState, useEffect, useRef } from 'react';

export function useWebSocket() {
  const [messages, setMessages] = useState([]);
  const [leadInfo, setLeadInfo] = useState({});
  const [callStatus, setCallStatus] = useState('Idle');
  const [transcript, setTranscript] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [actionStatus, setActionStatus] = useState({});
  const [summary, setSummary] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [rawState, setRawState] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard-ws`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setTimeout(connect, 3000); // Auto-reconnect
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleMessage(data);
      } catch (e) {
        console.error('Failed to parse WS message', e);
      }
    };

    wsRef.current = ws;
  };

  const handleMessage = (data) => {
    if (data.type === 'state_update') {
      setRawState(data.state);
      if (data.state.testMode) setTestMode(true);
      if (data.state.lead) setLeadInfo(data.state.lead);
      if (data.state.callStatus) setCallStatus(data.state.callStatus);
      if (data.state.actions) setActionStatus(data.state.actions);
      if (data.state.summary) setSummary(data.state.summary);
      if (data.state.metrics) setMetrics(data.state.metrics);
    } else if (data.type === 'transcript') {
      setTranscript((prev) => [...prev, data.payload]);
    } else if (data.type === 'lead_update') {
      setLeadInfo((prev) => ({ ...prev, ...data.payload }));
    } else if (data.type === 'call_status') {
      setCallStatus(data.payload.status);
    } else if (data.type === 'action_update') {
      setActionStatus((prev) => ({ ...prev, [data.payload.action]: data.payload.status }));
    } else if (data.type === 'metrics') {
      setMetrics(data.payload);
    }
  };

  return {
    messages,
    leadInfo,
    callStatus,
    transcript,
    metrics,
    isConnected,
    actionStatus,
    summary,
    testMode,
    rawState
  };
}
