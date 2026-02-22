using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace GestureEngine
{
    /// <summary>
    /// WebSocket client that connects to the GestureEngine Python server.
    /// Runs on a background thread and marshals events to Unity's main thread.
    /// </summary>
    public class GestureEngineClient : IDisposable
    {
        public string ServerUrl { get; set; } = "ws://localhost:8765/ws";
        public float ReconnectInterval { get; set; } = 3f;
        public int MaxReconnectAttempts { get; set; } = 0;
        public bool AutoReconnect { get; set; } = true;

        public bool IsConnected => _ws != null && _ws.State == WebSocketState.Open;

        /// <summary>Raw JSON messages queued for main-thread processing.</summary>
        public ConcurrentQueue<string> IncomingMessages { get; } = new ConcurrentQueue<string>();

        public event Action OnConnected;
        public event Action<string> OnDisconnected;
        public event Action<string> OnError;

        private ClientWebSocket _ws;
        private CancellationTokenSource _cts;
        private Thread _receiveThread;
        private volatile bool _disposed;
        private int _reconnectCount;

        /// <summary>
        /// Connect to the server. Non-blocking — starts background thread.
        /// </summary>
        public void Connect()
        {
            if (IsConnected) return;

            _cts?.Cancel();
            _cts = new CancellationTokenSource();
            _reconnectCount = 0;

            _receiveThread = new Thread(ReceiveLoop)
            {
                IsBackground = true,
                Name = "GestureEngine-WS"
            };
            _receiveThread.Start();
        }

        /// <summary>
        /// Disconnect from the server.
        /// </summary>
        public void Disconnect()
        {
            AutoReconnect = false;
            _cts?.Cancel();
            CloseSocket();
        }

        /// <summary>
        /// Send a JSON message to the server.
        /// </summary>
        public void Send(string json)
        {
            if (!IsConnected) return;
            try
            {
                var bytes = Encoding.UTF8.GetBytes(json);
                var segment = new ArraySegment<byte>(bytes);
                _ws.SendAsync(segment, WebSocketMessageType.Text, true, CancellationToken.None)
                    .ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[GestureEngine] Send error: {ex.Message}");
            }
        }

        private void ReceiveLoop()
        {
            var token = _cts.Token;

            while (!token.IsCancellationRequested && !_disposed)
            {
                try
                {
                    ConnectSync(token);
                    if (token.IsCancellationRequested) break;

                    OnConnected?.Invoke();

                    ReadMessages(token);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    OnError?.Invoke(ex.Message);
                }

                CloseSocket();
                OnDisconnected?.Invoke("Connection lost");

                if (!AutoReconnect || token.IsCancellationRequested) break;

                _reconnectCount++;
                if (MaxReconnectAttempts > 0 && _reconnectCount > MaxReconnectAttempts)
                {
                    OnError?.Invoke("Max reconnect attempts reached");
                    break;
                }

                // Wait before reconnecting
                try
                {
                    Thread.Sleep((int)(ReconnectInterval * 1000));
                }
                catch (ThreadInterruptedException)
                {
                    break;
                }
            }
        }

        private void ConnectSync(CancellationToken token)
        {
            _ws = new ClientWebSocket();
            var uri = new Uri(ServerUrl);
            _ws.ConnectAsync(uri, token).GetAwaiter().GetResult();
        }

        private void ReadMessages(CancellationToken token)
        {
            var buffer = new byte[8192];

            while (!token.IsCancellationRequested && _ws.State == WebSocketState.Open)
            {
                using (var ms = new MemoryStream())
                {
                    WebSocketReceiveResult result;
                    do
                    {
                        var segment = new ArraySegment<byte>(buffer);
                        result = _ws.ReceiveAsync(segment, token).GetAwaiter().GetResult();

                        if (result.MessageType == WebSocketMessageType.Close)
                            return;

                        ms.Write(buffer, 0, result.Count);
                    }
                    while (!result.EndOfMessage);

                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        var json = Encoding.UTF8.GetString(ms.ToArray());
                        IncomingMessages.Enqueue(json);
                    }
                }
            }
        }

        private void CloseSocket()
        {
            try
            {
                if (_ws != null && _ws.State == WebSocketState.Open)
                {
                    _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Client closing",
                        CancellationToken.None).GetAwaiter().GetResult();
                }
            }
            catch { }

            try { _ws?.Dispose(); } catch { }
            _ws = null;
        }

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;
            _cts?.Cancel();
            CloseSocket();
            _cts?.Dispose();
        }
    }
}
