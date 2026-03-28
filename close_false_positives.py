import requests, time

PAT = '$GITHUB_TOKEN'
REPO = 'EmpCloud/EmpCloud'
headers = {'Authorization': f'token {PAT}', 'Accept': 'application/vnd.github.v3+json'}

close_comment = ('Closing as false positive. The i18n key detection on this page was triggered '
                 'by the sidebar label "nav.myProfile" appearing on every page. '
                 'The actual untranslated sidebar key is tracked in #242.')

closed = 0
for num in range(211, 239):
    try:
        r = requests.get(f'https://api.github.com/repos/{REPO}/issues/{num}', headers=headers)
        if r.status_code != 200:
            continue
        issue = r.json()
        title = issue['title']
        if 'Raw i18n keys' not in title:
            print(f'SKIP #{num}: {title}')
            continue
        if issue['state'] == 'closed':
            print(f'SKIP #{num}: already closed')
            continue

        requests.post(f'https://api.github.com/repos/{REPO}/issues/{num}/comments',
                      headers=headers, json={'body': close_comment})

        r2 = requests.patch(f'https://api.github.com/repos/{REPO}/issues/{num}',
                           headers=headers, json={'state': 'closed', 'state_reason': 'not_planned'})
        if r2.status_code == 200:
            print(f'CLOSED #{num}: {title}')
            closed += 1
        else:
            print(f'FAIL close #{num}: {r2.status_code}')
        time.sleep(0.5)
    except Exception as e:
        print(f'ERROR #{num}: {str(e)[:100]}')

print(f'\nClosed {closed} false-positive issues')
