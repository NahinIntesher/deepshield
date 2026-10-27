import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/session.dart';
import '../ui/kit.dart';

class AuthPage extends StatefulWidget {
  final bool onboarding;
  const AuthPage({super.key, this.onboarding = false});
  @override
  State<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends State<AuthPage> {
  final form = GlobalKey<FormState>();
  final username = TextEditingController(),
      name = TextEditingController(),
      email = TextEditingController(),
      password = TextEditingController();
  bool signup = false, admin = false, visible = false, busy = false;
  String? error, message;
  @override
  void dispose() {
    for (final c in [username, name, email, password]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> submit() async {
    if (!form.currentState!.validate()) return;
    final app = AppScope.of(context);
    setState(() {
      busy = true;
      error = null;
      message = null;
    });
    try {
      if (widget.onboarding) {
        await app.api.post('/auth/onboarding', {
          'username': username.text.trim(),
          'display_name': name.text.trim(),
          if (password.text.isNotEmpty) 'password': password.text,
        });
        await app.refresh();
      } else if (signup) {
        final verify = await app.signup({
          'username': username.text.trim(),
          'display_name': name.text.trim(),
          'email': email.text.trim(),
          'password': password.text,
        });
        if (verify && mounted) {
          setState(
            () => message = app.t(
              'Check your email to verify your account before signing in.',
              'লগইনের আগে ইমেইলের লিংক থেকে অ্যাকাউন্ট ভেরিফাই করুন।',
            ),
          );
        }
      } else {
        await app.login(username.text, password.text, admin: admin);
      }
    } catch (e) {
      if (mounted) setState(() => error = app.t(Api.errorText(e)));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    String t(String e, String b) => app.t(e, b);
    return Scaffold(
      appBar: AppBar(
        title: const Brand(compact: true),
        actions: [
          TextButton(
            onPressed: app.toggleLanguage,
            child: Text(app.bengali ? 'Eng' : 'বাংলা'),
          ),
          IconButton(
            onPressed: app.toggleTheme,
            tooltip: t('Change theme', 'থিম বদলান'),
            icon: Icon(
              app.theme == ThemeMode.dark
                  ? Icons.light_mode_outlined
                  : Icons.dark_mode_outlined,
            ),
          ),
        ],
      ),
      body: AutofillGroup(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 28),
                  if (!widget.onboarding && !admin)
                    const Center(child: BrandMark(height: 58))
                  else
                    Icon(
                      widget.onboarding
                          ? Icons.person_outline
                          : admin
                          ? Icons.admin_panel_settings_outlined
                          : Icons.shield_outlined,
                      size: 58,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  const SizedBox(height: 24),
                  PageTitle(
                    widget.onboarding
                        ? t('Complete your profile', 'প্রোফাইল সম্পূর্ণ করুন')
                        : signup
                        ? t('Create your account', 'অ্যাকাউন্ট তৈরি করুন')
                        : admin
                        ? t('Administrator sign in', 'অ্যাডমিন লগইন')
                        : t('Welcome back', 'আবার স্বাগতম'),
                    subtitle: widget.onboarding
                        ? t(
                            'Choose your username and display name.',
                            'আপনার ইউজারনেম ও নাম বেছে নিন।',
                          )
                        : t(
                            'Check media. Learn the signs.',
                            'মিডিয়া যাচাই করুন। শনাক্ত করার কৌশল শিখুন।',
                          ),
                  ),
                  const SizedBox(height: 28),
                  Panel(
                    child: Form(
                      key: form,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          TextFormField(
                            key: const Key('username'),
                            controller: username,
                            enabled: !busy,
                            autofillHints: const [AutofillHints.username],
                            textInputAction: TextInputAction.next,
                            decoration: InputDecoration(
                              labelText: t('Username', 'ইউজারনেম'),
                              prefixIcon: const Icon(Icons.alternate_email),
                            ),
                            validator: (v) =>
                                v == null ||
                                    !RegExp(r'^[A-Za-z0-9_.-]{2,50}$')
                                        .hasMatch(v.trim())
                                ? t(
                                    'Use 2–50 letters, numbers, dots, _ or -.',
                                    '২–৫০টি ইংরেজি অক্ষর, সংখ্যা, ডট, _ বা - দিন।',
                                  )
                                : null,
                          ),
                          if (signup || widget.onboarding) ...[
                            const SizedBox(height: 18),
                            TextFormField(
                              controller: name,
                              enabled: !busy,
                              maxLength: 64,
                              autofillHints: const [AutofillHints.name],
                              textInputAction: TextInputAction.next,
                              decoration: InputDecoration(
                                labelText: t('Display name', 'আপনার নাম'),
                              ),
                              validator: (v) => (v ?? '').trim().isEmpty
                                  ? t('Enter your name.', 'আপনার নাম লিখুন।')
                                  : null,
                            ),
                          ],
                          if (signup) ...[
                            const SizedBox(height: 18),
                            TextFormField(
                              controller: email,
                              enabled: !busy,
                              keyboardType: TextInputType.emailAddress,
                              autofillHints: const [AutofillHints.email],
                              textInputAction: TextInputAction.next,
                              decoration: InputDecoration(
                                labelText: t('Email address', 'ইমেইল ঠিকানা'),
                              ),
                              validator: (v) =>
                                  !RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                                      .hasMatch(v ?? '')
                                  ? t(
                                      'Enter a valid email address.',
                                      'সঠিক ইমেইল ঠিকানা লিখুন।',
                                    )
                                  : null,
                            ),
                          ],
                          const SizedBox(height: 18),
                          TextFormField(
                            key: const Key('password'),
                            controller: password,
                            enabled: !busy,
                            obscureText: !visible,
                            autofillHints: [
                              signup
                                  ? AutofillHints.newPassword
                                  : AutofillHints.password,
                            ],
                            onFieldSubmitted: (_) => submit(),
                            decoration: InputDecoration(
                              labelText: widget.onboarding
                                  ? t(
                                      'Password (optional)',
                                      'পাসওয়ার্ড (ঐচ্ছিক)',
                                    )
                                  : t('Password', 'পাসওয়ার্ড'),
                              prefixIcon: const Icon(Icons.lock_outline),
                              suffixIcon: IconButton(
                                tooltip: t(
                                  visible ? 'Hide password' : 'Show password',
                                  visible
                                      ? 'পাসওয়ার্ড লুকান'
                                      : 'পাসওয়ার্ড দেখান',
                                ),
                                onPressed: () =>
                                    setState(() => visible = !visible),
                                icon: Icon(
                                  visible
                                      ? Icons.visibility_off_outlined
                                      : Icons.visibility_outlined,
                                ),
                              ),
                            ),
                            validator: (v) {
                              if (widget.onboarding && (v ?? '').isEmpty) {
                                return null;
                              }
                              final min = widget.onboarding ? 12 : 8;
                              return (v ?? '').length < min
                                  ? t(
                                      'Use at least $min characters.',
                                      'অন্তত $min অক্ষর দিন।',
                                    )
                                  : null;
                            },
                          ),
                          if (app.restoreError != null) ...[
                            const SizedBox(height: 18),
                            Notice(app.t(app.restoreError!), error: true),
                          ],
                          if (error != null) ...[
                            const SizedBox(height: 18),
                            Notice(error!, error: true),
                          ],
                          if (message != null) ...[
                            const SizedBox(height: 18),
                            Notice(message!),
                          ],
                          const SizedBox(height: 24),
                          BusyButton(
                            widget.onboarding
                                ? t('Save and continue', 'সেভ করে এগিয়ে যান')
                                : signup
                                ? t('Create account', 'অ্যাকাউন্ট তৈরি করুন')
                                : t('Sign in', 'লগইন'),
                            busy: busy,
                            onPressed: submit,
                            icon: Icons.arrow_forward,
                          ),
                          if (!admin && !widget.onboarding) ...[
                            const Padding(
                              padding: EdgeInsets.symmetric(vertical: 14),
                              child: Center(child: Text('—  Google  —')),
                            ),
                            OutlinedButton.icon(
                              onPressed: busy
                                  ? null
                                  : () async {
                                      try {
                                        await app.google();
                                      } catch (e) {
                                        if (mounted) {
                                          setState(
                                            () =>
                                                error = app.t(Api.errorText(e)),
                                          );
                                        }
                                      }
                                    },
                              icon: const Icon(Icons.open_in_browser),
                              label: Text(
                                t(
                                  'Continue with Google',
                                  'Google দিয়ে এগিয়ে যান',
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (!widget.onboarding) ...[
                    TextButton(
                      onPressed: busy
                          ? null
                          : () => setState(() {
                              signup = !signup;
                              admin = false;
                              error = null;
                              message = null;
                            }),
                      child: Text(
                        signup
                            ? t(
                                'Already have an account? Sign in',
                                'অ্যাকাউন্ট আছে? লগইন করুন',
                              )
                            : t(
                                'New here? Create an account',
                                'নতুন? অ্যাকাউন্ট তৈরি করুন',
                              ),
                      ),
                    ),
                    TextButton(
                      onPressed: busy
                          ? null
                          : () => setState(() {
                              admin = !admin;
                              signup = false;
                              error = null;
                            }),
                      child: Text(
                        admin
                            ? t('Member sign in', 'মেম্বার লগইন')
                            : t('Administrator access', 'অ্যাডমিন লগইন'),
                      ),
                    ),
                  ],
                  if (widget.onboarding)
                    TextButton(
                      onPressed: () => app.logout(),
                      child: Text(t('Sign out', 'সাইন আউট')),
                    ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
