#!/usr/bin/env python3
"""
Deploy fed-no-watch to GitHub.
Usage: Pass GitHub PAT via stdin (getpass prompt)
"""
import json, os, subprocess, sys, urllib.request, getpass
from pathlib import Path

OWNER = 'kindle0088-sys'
REPO = 'fed-no-watch'

def api(path, method='GET', payload=None):
    url = f'https://api.github.com{path}'
    token = os.environ.get('GITHUB_TOKEN') or getpass.getpass('[deploy] GitHub PAT: ')
    os.environ['GITHUB_TOKEN'] = token
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json' if data else 'application/vnd.github+json',
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8', errors='ignore')
        print(f'[API] {method} {path} -> HTTP {e.code}: {err[:300]}')
        raise

def main():
    # Get token from stdin if not in env
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        token = getpass.getpass('[deploy] GitHub PAT: ')
        os.environ['GITHUB_TOKEN'] = token

    # 1) Verify token
    status, user = api('/user')
    username = user.get('login')
    print(f'[OK] token ok, user={username}')

    # 2) Create repo if needed
    try:
        status, repo_data = api(f'/repos/{OWNER}/{REPO}')
        print(f'[OK] repo exists: {OWNER}/{REPO}')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            payload = {
                'name': REPO,
                'description': 'Daily Fed news, speeches, and market rate data',
                'private': False,
                'auto_init': False,
            }
            status, repo_data = api('/user/repos', method='POST', payload=payload)
            print(f'[OK] repo created: {OWNER}/{REPO}')
        else:
            raise

    # 3) Local git commit
    repo_path = Path('/home/admin/fed-no-watch')
    subprocess.run(['git', 'config', 'user.name', 'bot'], cwd=repo_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'bot@fed-no-watch.example'], cwd=repo_path, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=repo_path, check=True)
    try:
        subprocess.run(['git', 'commit', '-m', 'Initial commit: fed-no-watch static site'],
                      cwd=repo_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('[OK] local commit created')
    except subprocess.CalledProcessError:
        print('[INFO] no new commit needed (already committed)')

    # 4) Push to GitHub (with token via HTTP header)
    remote_url = f'https://github.com/{OWNER}/{REPO}.git'
    # Remove existing origin if any
    try:
        subprocess.run(['git', 'remote', 'remove', 'origin'], cwd=repo_path, check=True,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass
    subprocess.run(['git', 'remote', 'add', 'origin', remote_url], cwd=repo_path, check=True)
    print('[OK] remote origin set')

    cmd = ['git', '-c', f'http.extraHeader=Authorization: Bearer {token}',
           'push', '-u', 'origin', 'main']
    res = subprocess.run(cmd, cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print('[ERR] git push failed')
        print(res.stdout)
        print(res.stderr)
        sys.exit(res.returncode)
    print('[OK] pushed main branch')

    # 5) Enable Pages on main branch / (root) — simpler than gh-pages
    # Actually our workflow builds to gh-pages, but first we can enable Pages
    # on main branch /docs or /root for static site while workflow runs
    # But for now, enable on root of gh-pages branch (workflow pushes there)
    try:
        status, pages = api(f'/repos/{OWNER}/{REPO}/pages', method='POST',
            payload={'source': {'branch': 'gh-pages', 'path': '/'}})
        print('[OK] Pages enabled on gh-pages branch')
    except urllib.error.HTTPError as e:
        # 409 may mean pages already enabled
        if e.code == 409:
            print('[INFO] Pages already configured')
        else:
            print(f'[WARN] Pages enable returned HTTP {e.code} — may need manual setup')

    print(f'[DONE] URL: https://{OWNER}.github.io/{REPO}/')

if __name__ == '__main__':
    main()
