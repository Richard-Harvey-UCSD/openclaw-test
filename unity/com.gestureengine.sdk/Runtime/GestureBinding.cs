using System;
using UnityEngine;
using UnityEngine.Events;

namespace GestureEngine
{
    /// <summary>
    /// Maps gestures to UnityEvents in the Inspector.
    /// Attach to any GameObject to create gesture-driven behaviors.
    /// </summary>
    public class GestureBinding : MonoBehaviour
    {
        [SerializeField] private Binding[] bindings = new Binding[0];

        private void OnEnable()
        {
            var manager = GestureManager.Instance;
            if (manager != null)
            {
                manager.OnGesture.AddListener(HandleGesture);
                manager.OnSequence.AddListener(HandleSequence);
                manager.OnBimanual.AddListener(HandleBimanual);
                manager.OnTrajectory.AddListener(HandleTrajectory);
            }
        }

        private void OnDisable()
        {
            var manager = GestureManager.Instance;
            if (manager != null)
            {
                manager.OnGesture.RemoveListener(HandleGesture);
                manager.OnSequence.RemoveListener(HandleSequence);
                manager.OnBimanual.RemoveListener(HandleBimanual);
                manager.OnTrajectory.RemoveListener(HandleTrajectory);
            }
        }

        private void HandleGesture(GestureEvent evt)
        {
            foreach (var binding in bindings)
            {
                if (!binding.enabled) continue;
                if (binding.eventType != BindingEventType.Gesture) continue;
                if (binding.gestureName != evt.gesture) continue;
                if (evt.confidence < binding.minimumConfidence) continue;
                if (!binding.CheckCooldown()) continue;

                binding.onTriggered?.Invoke();
                binding.onTriggeredWithConfidence?.Invoke(evt.confidence);
            }
        }

        private void HandleSequence(GestureSequenceEvent evt)
        {
            foreach (var binding in bindings)
            {
                if (!binding.enabled) continue;
                if (binding.eventType != BindingEventType.Sequence) continue;
                if (binding.gestureName != evt.sequence) continue;
                if (!binding.CheckCooldown()) continue;

                binding.onTriggered?.Invoke();
            }
        }

        private void HandleBimanual(BimanualEvent evt)
        {
            foreach (var binding in bindings)
            {
                if (!binding.enabled) continue;
                if (binding.eventType != BindingEventType.Bimanual) continue;
                if (binding.gestureName != evt.gesture) continue;
                if (evt.confidence < binding.minimumConfidence) continue;
                if (!binding.CheckCooldown()) continue;

                binding.onTriggered?.Invoke();
                binding.onTriggeredWithConfidence?.Invoke(evt.confidence);
            }
        }

        private void HandleTrajectory(TrajectoryEvent evt)
        {
            foreach (var binding in bindings)
            {
                if (!binding.enabled) continue;
                if (binding.eventType != BindingEventType.Trajectory) continue;
                if (binding.gestureName != evt.name) continue;
                if (evt.score < binding.minimumConfidence) continue;
                if (!binding.CheckCooldown()) continue;

                binding.onTriggered?.Invoke();
                binding.onTriggeredWithConfidence?.Invoke(evt.score);
            }
        }
    }

    public enum BindingEventType
    {
        Gesture,
        Sequence,
        Bimanual,
        Trajectory
    }

    /// <summary>
    /// A single gesture-to-action binding with confidence and cooldown settings.
    /// </summary>
    [Serializable]
    public class Binding
    {
        public bool enabled = true;
        public BindingEventType eventType = BindingEventType.Gesture;
        public string gestureName = "open_hand";

        [Range(0f, 1f)]
        public float minimumConfidence = 0.6f;

        [Tooltip("Minimum seconds between triggers")]
        [Range(0f, 10f)]
        public float cooldown = 0.5f;

        public UnityEvent onTriggered = new UnityEvent();

        [Tooltip("Invoked with the confidence/score value")]
        public FloatUnityEvent onTriggeredWithConfidence = new FloatUnityEvent();

        private float _lastTriggerTime = -999f;

        public bool CheckCooldown()
        {
            if (Time.time - _lastTriggerTime < cooldown)
                return false;
            _lastTriggerTime = Time.time;
            return true;
        }

        [Serializable]
        public class FloatUnityEvent : UnityEvent<float> { }
    }
}
