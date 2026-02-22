using UnityEngine;
using GestureEngine;

/// <summary>
/// Simple demo: logs all gesture events to the console.
/// Attach to any GameObject in a scene that has a GestureManager.
/// </summary>
public class BasicGestureDemo : MonoBehaviour
{
    private void OnEnable()
    {
        GestureManager.Instance.OnGesture.AddListener(OnGesture);
        GestureManager.Instance.OnSequence.AddListener(OnSequence);
        GestureManager.Instance.OnBimanual.AddListener(OnBimanual);
        GestureManager.Instance.OnTrajectory.AddListener(OnTrajectory);
    }

    private void OnDisable()
    {
        if (GestureManager.Instance != null)
        {
            GestureManager.Instance.OnGesture.RemoveListener(OnGesture);
            GestureManager.Instance.OnSequence.RemoveListener(OnSequence);
            GestureManager.Instance.OnBimanual.RemoveListener(OnBimanual);
            GestureManager.Instance.OnTrajectory.RemoveListener(OnTrajectory);
        }
    }

    private void OnGesture(GestureEvent evt)
    {
        Debug.Log($"🤚 Gesture: {evt.gesture} (confidence: {evt.confidence:F2}, hand: {evt.hand_index})");
    }

    private void OnSequence(GestureSequenceEvent evt)
    {
        Debug.Log($"🔗 Sequence: {evt.sequence} ({string.Join(" → ", evt.gestures)})");
    }

    private void OnBimanual(BimanualEvent evt)
    {
        Debug.Log($"🙌 Bimanual: {evt.gesture} (value: {evt.value:F3})");
    }

    private void OnTrajectory(TrajectoryEvent evt)
    {
        Debug.Log($"👆 Trajectory: {evt.name} (score: {evt.score:F2})");
    }
}
