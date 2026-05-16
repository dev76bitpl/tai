# Changelog

## [0.1.3](https://github.com/dev76bitpl/ai/compare/v0.1.2...v0.1.3) (2026-05-16)


### Bug Fixes

* **scripts:** Add package.json with doctor and prepare scripts ([#15](https://github.com/dev76bitpl/ai/issues/15)) ([3c56673](https://github.com/dev76bitpl/ai/commit/3c5667396f5f55d623e1fb11011dbbbaf1923d83))

## [0.1.2](https://github.com/dev76bitpl/ai/compare/v0.1.1...v0.1.2) (2026-05-16)


### Features

* **guard:** Add guard_typecheck — tsc --noEmit as pre-commit hook ([7e613bc](https://github.com/dev76bitpl/ai/commit/7e613bcb5c76c84e33bfabd7c288feb34d05d77f))
* **guard:** Extend guard-template-sync to check scripts/dev-guards/*.py content ([7264959](https://github.com/dev76bitpl/ai/commit/7264959bce16c20211325a767cf28eefb48e2f25))
* **guards:** Add guard-release-tag to detect missing release tags ([14e77a9](https://github.com/dev76bitpl/ai/commit/14e77a93996d8c300f7b65c6b6b3fb01c2304939))
* **guards:** Add guard-release-tag to detect missing release tags ([15fb515](https://github.com/dev76bitpl/ai/commit/15fb515b22829ca0e0cc09270b44cc2c1e22bd2b))


### Bug Fixes

* **ci:** Add pull-request-title-pattern to release-please config ([cfac58a](https://github.com/dev76bitpl/ai/commit/cfac58a623aebfe52763dd89948c11efbc89bbf7))
* **guards:** Use GitHub Release instead of git tag in guard-release-tag ([#7](https://github.com/dev76bitpl/ai/issues/7)) ([9bf9597](https://github.com/dev76bitpl/ai/commit/9bf959743afc15aeee7260381ab5537b974eada4))
* **hooks:** Move hook commands to settings.local.json (cross-platform) ([#13](https://github.com/dev76bitpl/ai/issues/13)) ([78ce873](https://github.com/dev76bitpl/ai/commit/78ce873cda0c345d0b6267fd1a5c9c98fe49b8cc))

## [0.1.1](https://github.com/dev76bitpl/ai/compare/v0.1.0...v0.1.1) (2026-05-13)


### Features

* Add full template structure ([caa901e](https://github.com/dev76bitpl/ai/commit/caa901e4595756b58ece09566293a3b9099e090b))
* **guards:** Adopt pre-commit framework + release-please ([d99c1eb](https://github.com/dev76bitpl/ai/commit/d99c1eb311fa5faaa4d216c7dc2feea6f3b2b53d))
* **guards:** Adopt pre-commit framework + release-please ([6635b13](https://github.com/dev76bitpl/ai/commit/6635b13e5586e547caad368d4bec13f3e2e81bfe))
* **hooks:** Add module closure protocol with user-tested guard ([427ca39](https://github.com/dev76bitpl/ai/commit/427ca392f3c56511331effdb98f883e1dd1d8488))
* **hooks:** Filter TASKS.md to open tasks only in session context ([4fe8119](https://github.com/dev76bitpl/ai/commit/4fe81199085fe38a94390dcd242adfa96687fb59))
* **hooks:** Suggest-pr — detect merged branches after pull/checkout main ([8109d3a](https://github.com/dev76bitpl/ai/commit/8109d3ada307057c016b180d7d1af5430d445ed5))
* **hooks:** Suggest-pr PostToolUse hook — remind after git commit on feat/fix branch ([ac60f51](https://github.com/dev76bitpl/ai/commit/ac60f511154157c2478f21440343580ed90ac2ec))
* **workflow:** AI proactively proposes PR after closing commit on branch ([501f91a](https://github.com/dev76bitpl/ai/commit/501f91a371bd5029899ad580f9840ee05cbb2ec3))
* **workflow:** AI waits for user to confirm merge before proceeding ([48380fd](https://github.com/dev76bitpl/ai/commit/48380fd0365e7748c140cc209fd4d21de11d96e2))


### Bug Fixes

* **ci:** Scope commit-msg loop to gitlint + guard-commit-lang ([7671898](https://github.com/dev76bitpl/ai/commit/767189841e1abb9e13ff683fd175bf82323f6cd2))
* **ci:** Skip no-commit-to-branch on main + GitHub settings doc ([1334cd1](https://github.com/dev76bitpl/ai/commit/1334cd19ddda23422b1c63d3c4d9bfe053d662ab))
* **ci:** Skip no-commit-to-branch when running pre-commit on main ([df1de91](https://github.com/dev76bitpl/ai/commit/df1de91cd187362bc7becfd76979ee9b38797662))
* **hooks:** Account for `git add X && git commit` chained commands in PreToolUse guards ([a8afc8f](https://github.com/dev76bitpl/ai/commit/a8afc8f80634962911bd80836420c44962b7cbec))
* **hooks:** Account for `git add X && git commit` chained commands in PreToolUse guards (gh pr create false positive) ([c30bb08](https://github.com/dev76bitpl/ai/commit/c30bb080e095d9a690b37276fd000b83e2551bbe))
* **hooks:** Add PowerShell heredoc parsing to pre-commit extract_commit_message ([13d1ff1](https://github.com/dev76bitpl/ai/commit/13d1ff13f27eaf32042317067620bded184fde49))
* **hooks:** Add PowerShell support to hook matchers and commit message parser ([fc3bbec](https://github.com/dev76bitpl/ai/commit/fc3bbec21a91468407218b248d1ef953cc22a4a0))
* **hooks:** Always display open tasks to user at session start ([8e98a17](https://github.com/dev76bitpl/ai/commit/8e98a179283ab3c6be2da70e2b9417f01eabcd73))
* **hooks:** Change --bail to --bail=1 in vitest node test command [no-template] [skip-docs] ([75df9a4](https://github.com/dev76bitpl/ai/commit/75df9a4a15c7cd3f62aa0a37b22890c3b90cdc87))
* **hooks:** Cross-platform session dir, add UserPromptSubmit hook ([00b8e44](https://github.com/dev76bitpl/ai/commit/00b8e44fe4b02b8c2273865b2748756490f3b517))
* **hooks:** Force UTF-8 stdout/stderr for Windows cp1250 compat ([a5bf138](https://github.com/dev76bitpl/ai/commit/a5bf13821ea46f55bffdb560683a2308f82446a0))
* **hooks:** Guard-adr uses get_staged_files; guard-ai-template parses PS heredoc ([cdbe4e9](https://github.com/dev76bitpl/ai/commit/cdbe4e9341f9308977d36acfc45eef0c95f29051))
* **hooks:** Normalize Git for Windows paths in get_project_root ([1ae7a1e](https://github.com/dev76bitpl/ai/commit/1ae7a1ee5c1b2133ca09b6e9009365a355efd5c7))
* **hooks:** Prevent chdir to external repos in chdir_to_project_root ([2f0d5ac](https://github.com/dev76bitpl/ai/commit/2f0d5ac08896b17e3ee93b989a35b2a6d19a7a3a))
* **hooks:** Remove project-name marker logic + parameterize template path ([3a4c736](https://github.com/dev76bitpl/ai/commit/3a4c736f558688b94816fad0e438b934cc83d4b0))
* **hooks:** Skip guards when git command targets a foreign repo [no-template] [skip-docs] ([5e01fe4](https://github.com/dev76bitpl/ai/commit/5e01fe475f180d4fdd8846cce465233614c4474f))
* **hooks:** Stack.py — handle ; separator in is_git_commit_command and get_command_git_cwd ([77e2f90](https://github.com/dev76bitpl/ai/commit/77e2f902162e0f5aeb027764710abcdbf2476c91))
* **hooks:** Strip quotes from staged file tokens in get_staged_files ([717fc03](https://github.com/dev76bitpl/ai/commit/717fc03af7f32886e3035e1fb4b75c28f27cd658))
* **pre-commit:** Handle heredoc in subshell and skip lint for docs-only commits ([e6608ad](https://github.com/dev76bitpl/ai/commit/e6608ad8d67e4bc6873cfee8eb2c0b094c23b417))
