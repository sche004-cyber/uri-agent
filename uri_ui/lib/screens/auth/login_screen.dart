import 'package:flutter/material.dart';

import '../../services/uri_client.dart';
import '../../theme/uri_theme.dart';

/// Prototype 1 (multi-user identity): the minimum login/signup flow
/// needed to prove one URI server can serve multiple isolated users -
/// not a redesign of the app, and not real production authentication
/// (no OAuth/Gmail/GitHub - see uri_core/core/user_accounts.py). Shown
/// before onboarding/the main shell whenever [AppState.isAuthenticated]
/// is false; disappears the moment [onLogin]/[onSignup] succeeds.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onLogin, required this.onSignup});

  final Future<AuthOutcome> Function(String username, String password) onLogin;
  final Future<AuthOutcome> Function(String username, String password) onSignup;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _isSignupMode = false;
  bool _isSubmitting = false;
  String? _errorText;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text;

    if (username.isEmpty || password.isEmpty) {
      setState(() => _errorText = 'Enter a username and password.');
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorText = null;
    });

    final outcome = _isSignupMode
        ? await widget.onSignup(username, password)
        : await widget.onLogin(username, password);

    if (!mounted) return;

    setState(() {
      _isSubmitting = false;
      _errorText = outcome.success ? null : (outcome.message ?? 'Something went wrong.');
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = UriColors.of(context);

    return Scaffold(
      backgroundColor: colors.canvas,
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Padding(
              padding: const EdgeInsets.all(UriSpace.xl),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _isSignupMode ? 'Create your URI account' : 'Sign in to URI',
                    style: theme.textTheme.headlineMedium,
                  ),
                  const SizedBox(height: UriSpace.xs),
                  Text(
                    _isSignupMode
                        ? 'This creates your own private URI space on this server — separate from everyone else who signs in here.'
                        : 'Each account has its own private URI space — profile, memory, tasks, and approvals never cross between accounts.',
                    style: theme.textTheme.bodyMedium,
                  ),
                  const SizedBox(height: UriSpace.lg),
                  TextField(
                    controller: _usernameController,
                    autofillHints: const [AutofillHints.username],
                    decoration: const InputDecoration(labelText: 'Username'),
                    onSubmitted: (_) => _submit(),
                  ),
                  const SizedBox(height: UriSpace.sm),
                  TextField(
                    controller: _passwordController,
                    obscureText: true,
                    autofillHints: const [AutofillHints.password],
                    decoration: const InputDecoration(labelText: 'Password'),
                    onSubmitted: (_) => _submit(),
                  ),
                  if (_errorText != null) ...[
                    const SizedBox(height: UriSpace.sm),
                    Text(
                      _errorText!,
                      style: theme.textTheme.bodyMedium?.copyWith(color: colors.danger),
                    ),
                  ],
                  const SizedBox(height: UriSpace.lg),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _isSubmitting ? null : _submit,
                      child: _isSubmitting
                          ? const SizedBox(
                              height: 18,
                              width: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Text(_isSignupMode ? 'Create account' : 'Sign in'),
                    ),
                  ),
                  const SizedBox(height: UriSpace.sm),
                  TextButton(
                    onPressed: _isSubmitting
                        ? null
                        : () => setState(() {
                            _isSignupMode = !_isSignupMode;
                            _errorText = null;
                          }),
                    child: Text(
                      _isSignupMode
                          ? 'Already have an account? Sign in'
                          : "New here? Create an account",
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
