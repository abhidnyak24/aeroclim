# Hosting the dashboard

The dashboard's public address is [aeroclim.live](https://aeroclim.live/). GitHub Pages serves the standalone HTML from `demo/index.html`. DNS and HTTPS must finish provisioning before the custom address is reachable.

## Deployment

The [Deploy dashboard workflow](../.github/workflows/pages.yml) runs the browser calculation tests, uploads only `demo/`, and deploys that artifact to GitHub Pages. The Python system, firmware, hardware files and documentation are not part of the published website. The repository can remain private while the dashboard is public; private-repository Pages requires an eligible GitHub plan.

The repository's **Settings → Pages → Build and deployment → Source** must be **GitHub Actions**. The custom domain is **aeroclim.live**. With an Actions deployment, the custom domain is managed in Pages settings rather than a repository `CNAME` file.

Changes to `demo/`, the browser test or the deployment workflow on `main` trigger deployment. The workflow can also be started manually from the Actions tab and only deploys `main`.

## Name.com DNS

Use Name.com's authoritative nameservers and these records. Name.com represents the apex host with an empty Host field.

| Type | Host | Answer |
| --- | --- | --- |
| A | Leave blank | `185.199.108.153` |
| A | Leave blank | `185.199.109.153` |
| A | Leave blank | `185.199.110.153` |
| A | Leave blank | `185.199.111.153` |
| CNAME | `www` | `abhidnyak24.github.io` |

Preserve unrelated records such as email MX and verification TXT records. Replace conflicting apex website records only when moving the website to Pages. Do not add a wildcard record.

GitHub issues the HTTPS certificate after DNS validation. Once the certificate is ready, enable **Enforce HTTPS** in Pages settings. GitHub handles the `www.aeroclim.live` redirect to the configured apex domain.

## Updating the website

1. Edit or replace `demo/index.html` with the desired dashboard.
2. Run `node --test tests/test_demo.cjs` from the repository root.
3. Commit and push the change to `main`.
4. Confirm that **Deploy dashboard** succeeds in the repository Actions tab.
5. Open [aeroclim.live](https://aeroclim.live/) and check the updated page.

No JavaScript dependency installation or build is required. The published HTML runs in the visitor's browser; live regional weather requests go directly to Open-Meteo. The website does not run the Python collector or receive ESP32 telemetry.

Reference: [GitHub custom-domain configuration](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site), [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages), and [Name.com DNS records and templates](https://cs.name.com/hc/en-us/articles/206127137-Adding-DNS-records-and-templates).
