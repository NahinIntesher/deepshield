import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/session.dart';
import '../ui/kit.dart';
import 'admin.dart';
import 'live_guard.dart';
import 'content.dart';
import 'member.dart';
import 'play.dart';
import 'scans.dart';
import 'guide.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int index = 0;
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final pages = app.admin
        ? <Widget>[
            const AdminOverview(),
            const UsersPage(),
            const ContentPage(),
            const MorePage(),
          ]
        : <Widget>[
            const HomePage(),
            const LiveGuardPage(),
            const ScanPage(),
            const LearnPage(),
            const MorePage(),
          ];
    final titles = app.admin
        ? ['Overview', 'Users', 'Content', 'More']
        : ['Overview', 'Live Guard', 'Scan', 'Learn', 'More'];
    final icons = app.admin
        ? [
            Icons.dashboard_outlined,
            Icons.people_outline,
            Icons.menu_book_outlined,
            Icons.grid_view_outlined,
          ]
        : [
            Icons.dashboard_outlined,
            Icons.sensors,
            Icons.document_scanner_outlined,
            Icons.school_outlined,
            Icons.grid_view_outlined,
          ];
    return LayoutBuilder(
      builder: (context, c) {
        final wide = c.maxWidth >= 800;
        return Scaffold(
          appBar: AppBar(
            title: Brand(compact: true, showName: c.maxWidth >= 380),
            actions: [
              TextButton(
                onPressed: app.toggleLanguage,
                child: Text(app.bengali ? 'Eng' : 'বাংলা'),
              ),
              IconButton(
                tooltip: app.t('Change theme', 'থিম বদলান'),
                onPressed: app.toggleTheme,
                icon: Icon(
                  app.theme == ThemeMode.dark
                      ? Icons.light_mode_outlined
                      : Icons.dark_mode_outlined,
                ),
              ),
              IconButton(
                tooltip: app.t('Notifications'),
                onPressed: () => openPage(
                  context,
                  app.t('Notifications'),
                  const NotificationsPage(),
                ),
                icon: const Icon(Icons.notifications_none),
              ),
            ],
          ),
          body: SafeArea(
            child: Row(
              children: [
                if (wide) ...[
                  NavigationRail(
                    selectedIndex: index,
                    onDestinationSelected: (v) => setState(() => index = v),
                    labelType: NavigationRailLabelType.all,
                    destinations: List.generate(
                      pages.length,
                      (i) => NavigationRailDestination(
                        icon: Icon(icons[i]),
                        label: Text(app.t(titles[i])),
                      ),
                    ),
                  ),
                  const VerticalDivider(width: 1),
                ],
                Expanded(
                  child: KeyedSubtree(
                    key: ValueKey('${app.admin}:$index'),
                    child: pages[index],
                  ),
                ),
              ],
            ),
          ),
          bottomNavigationBar: wide
              ? null
              : NavigationBar(
                  selectedIndex: index,
                  onDestinationSelected: (v) => setState(() => index = v),
                  destinations: List.generate(
                    pages.length,
                    (i) => NavigationDestination(
                      icon: Icon(icons[i]),
                      label: app.t(titles[i]),
                    ),
                  ),
                ),
        );
      },
    );
  }
}

class MorePage extends StatelessWidget {
  const MorePage({super.key});
  @override
  Widget build(BuildContext context) {
    final app = AppScope.of(context);
    final entries = app.admin
        ? <(String, IconData, Widget)>[
            ('Live Guard', Icons.sensors, const LiveGuardPage()),
            ('Records', Icons.storage_outlined, const RecordsPage()),
            (
              'Activity analytics',
              Icons.insights_outlined,
              const AdminOverview(),
            ),
            (
              'Research reviews',
              Icons.science_outlined,
              const TrainingPage(reviewOnly: true),
            ),
            ('Continual learning', Icons.model_training, const TrainingPage()),
            (
              'Service operations',
              Icons.settings_suggest_outlined,
              const OperationsPage(),
            ),
            ('Audit trail', Icons.receipt_long_outlined, const AuditPage()),
          ]
        : <(String, IconData, Widget)>[
            ('Scan history', Icons.history, const HistoryPage()),
            ('Real vs Fake', Icons.sports_esports_outlined, const PlayPage()),
            (
              'Leaderboard',
              Icons.emoji_events_outlined,
              const LeaderboardPage(),
            ),
            (
              'Learning assessment',
              Icons.assessment_outlined,
              const AssessmentPage(),
            ),
            (
              'Research challenge',
              Icons.science_outlined,
              const ResearchPage(),
            ),
            (
              'Research insights',
              Icons.insights_outlined,
              const InsightsPage(),
            ),
            (
              'Plans & subscription',
              Icons.workspace_premium_outlined,
              const SubscriptionPage(),
            ),
            ('Browser Companion', Icons.web, const CompanionPage()),
            ('Help & support', Icons.help_outline, const SupportPage()),
            ('My account', Icons.person_outline, const ProfilePage()),
          ];
    entries.add(('User guide', Icons.menu_book_outlined, const GuidePage()));
    return PageBody(
      children: [
        PageTitle(
          app.t('Your workspace', 'আপনার ওয়ার্কস্পেস'),
          subtitle: '${app.user!['display_name']} · @${app.user!['username']}',
        ),
        Panel(
          child: Column(
            children: entries
                .map(
                  (e) => ItemRow(
                    app.t(e.$1),
                    icon: e.$2,
                    onTap: () => openPage(context, app.t(e.$1), e.$3),
                  ),
                )
                .toList(),
          ),
        ),
        Panel(
          child: Column(
            children: [
              ItemRow(
                app.t('Language', 'ভাষা'),
                subtitle: app.bengali ? 'বাংলা' : 'English',
                icon: Icons.translate,
                onTap: app.toggleLanguage,
              ),
              ItemRow(
                app.t('Appearance', 'থিম'),
                subtitle: app.t(app.theme == ThemeMode.dark ? 'Dark' : 'Light'),
                icon: Icons.contrast,
                onTap: app.toggleTheme,
              ),
              ItemRow(
                app.t('About & licenses', 'অ্যাপের তথ্য ও লাইসেন্স'),
                icon: Icons.info_outline,
                onTap: () => showAboutDialog(
                  context: context,
                  applicationName: 'DeepShield',
                  applicationVersion: '1.0.0',
                  applicationLegalese: 'DeepShield · Team Hexagon',
                ),
              ),
            ],
          ),
        ),
        OutlinedButton.icon(
          icon: const Icon(Icons.logout),
          label: Text(app.t('Sign out', 'সাইন আউট')),
          onPressed: () async {
            if (!await confirmAction(
              context,
              app.t('Sign out?', 'সাইন আউট করবেন?'),
              app.t(
                'You can sign in again on this device.',
                'এই ডিভাইসে আবার লগইন করতে পারবেন।',
              ),
            )) {
              return;
            }
            try {
              await app.logout();
            } catch (e) {
              if (context.mounted) snack(context, app.t(Api.errorText(e)));
            }
          },
        ),
        const Center(child: Muted('DeepShield · Team Hexagon')),
      ],
    );
  }
}
