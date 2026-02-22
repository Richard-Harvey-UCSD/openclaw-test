using UnityEngine;
using GestureEngine;

/// <summary>
/// Move a character using hand gestures.
/// - Open hand: move forward
/// - Fist: stop
/// - Peace: jump
/// - Swipe left/right: turn
/// - Pointing: sprint forward
/// </summary>
[RequireComponent(typeof(CharacterController))]
public class GesturePlayerController : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float walkSpeed = 3f;
    [SerializeField] private float sprintSpeed = 6f;
    [SerializeField] private float turnSpeed = 90f;
    [SerializeField] private float jumpForce = 5f;
    [SerializeField] private float gravity = -9.81f;

    private CharacterController _controller;
    private Vector3 _velocity;
    private bool _moving;
    private bool _sprinting;
    private float _turnInput;

    private void Awake()
    {
        _controller = GetComponent<CharacterController>();
    }

    private void OnEnable()
    {
        var gm = GestureManager.Instance;
        gm.RegisterGesture("open_hand", OnOpenHand);
        gm.RegisterGesture("fist", OnFist);
        gm.RegisterGesture("peace", OnPeace);
        gm.RegisterGesture("pointing", OnPointing);
        gm.OnTrajectory.AddListener(OnTrajectory);
    }

    private void OnDisable()
    {
        var gm = GestureManager.Instance;
        if (gm != null)
        {
            gm.UnregisterGesture("open_hand", OnOpenHand);
            gm.UnregisterGesture("fist", OnFist);
            gm.UnregisterGesture("peace", OnPeace);
            gm.UnregisterGesture("pointing", OnPointing);
            gm.OnTrajectory.RemoveListener(OnTrajectory);
        }
    }

    private void Update()
    {
        // Apply turn
        if (Mathf.Abs(_turnInput) > 0.01f)
        {
            transform.Rotate(0, _turnInput * turnSpeed * Time.deltaTime, 0);
            _turnInput = Mathf.Lerp(_turnInput, 0, Time.deltaTime * 5f);
        }

        // Apply movement
        float speed = _sprinting ? sprintSpeed : walkSpeed;
        Vector3 move = _moving ? transform.forward * speed : Vector3.zero;

        // Gravity
        if (_controller.isGrounded && _velocity.y < 0)
            _velocity.y = -2f;
        _velocity.y += gravity * Time.deltaTime;

        _controller.Move((move + _velocity) * Time.deltaTime);
    }

    private void OnOpenHand(GestureEvent evt)
    {
        _moving = true;
        _sprinting = false;
    }

    private void OnFist(GestureEvent evt)
    {
        _moving = false;
        _sprinting = false;
    }

    private void OnPeace(GestureEvent evt)
    {
        if (_controller.isGrounded)
            _velocity.y = jumpForce;
    }

    private void OnPointing(GestureEvent evt)
    {
        _moving = true;
        _sprinting = true;
    }

    private void OnTrajectory(TrajectoryEvent evt)
    {
        if (evt.name == "swipe_left")
            _turnInput = -1f;
        else if (evt.name == "swipe_right")
            _turnInput = 1f;
    }
}
