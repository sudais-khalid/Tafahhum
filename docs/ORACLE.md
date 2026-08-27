# Deploying Tafahhum on Oracle Cloud Always Free

Oracle's Always Free tier is the only free option that actually fits this
project. The reason is the database: Tafahhum's corpus is several gigabytes,
and every other free Postgres tier caps at 500 MB to 1 GB.

| Provider | Free Postgres | Verdict |
|---|---|---|
| Supabase | 500 MB | Too small |
| Neon | 512 MB | Too small |
| Render | 1 GB, expires after 30 days | Too small, then gone |
| Fly.io | 3 GB volume | Tight, needs a reduced corpus |
| **Oracle Always Free** | **200 GB block storage** | **Fits** |

The Ampere A1 shape gives 4 OCPU and 24 GB RAM permanently free, which is more
than the laptop this was developed on.

## Before you start

Two things are true about this tier and neither is a secret:

- **Capacity is often unavailable** in popular regions. The signup will say
  "out of capacity" for the Ampere shape. This is normal and it clears; people
  retry over several days. Choose a less busy home region if you can.
- **A payment card is required for identity verification.** The Always Free
  resources stay free, but you must not let the account upgrade to Pay As You
  Go while it holds resources you expect to be free.

## 1. Create the instance

In the Oracle Cloud console, Compute, Instances, Create instance:

- **Shape**: `VM.Standard.A1.Flex`, 4 OCPU, 24 GB memory
- **Image**: Canonical Ubuntu 24.04 (aarch64)
- **Boot volume**: 100 GB, leaving room under the 200 GB free allowance
- **SSH key**: upload your public key

Note the public IP.

## 2. Open the ports

Two layers block traffic and both must be opened. Forgetting the second is the
single most common reason a correctly deployed instance appears dead.

**Layer 1, the VCN security list.** Networking, Virtual Cloud Networks, your
VCN, Security Lists, Default Security List, Add Ingress Rules:

| Source | Protocol | Port | For |
|---|---|---|---|
| 0.0.0.0/0 | TCP | 80 | HTTP, and the certificate challenge |
| 0.0.0.0/0 | TCP | 443 | HTTPS |

**Layer 2, the instance firewall.** Ubuntu images on Oracle ship with iptables
rules that drop everything except SSH, independently of the security list:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Do not open 5432. The database is on an internal Docker network and must never
be reachable from outside the host.

## 3. Install Docker

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

## 4. Point a domain at it

Caddy obtains a certificate automatically, but only for a real hostname. Create
an A record for your domain pointing at the instance's public IP and wait for
it to resolve before starting the stack. Starting Caddy before DNS resolves
burns Let's Encrypt rate limit attempts against a name that does not yet exist.

## 5. Configure and start

```bash
git clone https://github.com/sudais-khalid/Tafahhum.git
cd Tafahhum
cp .env.example .env
```

Edit `.env`:

```
POSTGRES_PASSWORD=<a long random string>
TAFAHHUM_DOMAIN=tafahhum.example.com
TAFAHHUM_CORS_ORIGINS=https://tafahhum.example.com
REGISTRY=ghcr.io/sudais-khalid/tafahhum
TAG=latest
```

Generate the password rather than inventing one:

```bash
openssl rand -base64 32
```

Then:

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api python -m tafahhum.db.migrate
```

The images are built for `linux/amd64` and `linux/arm64`, so the Ampere shape
pulls the arm64 variant without any change on your side.

## 6. Load the corpus

The images ship with no data. The corpus is roughly 2 GB of cached JSON and
several gigabytes in Postgres, so do this on the instance rather than uploading
a database dump over a home connection.

```bash
docker compose -f docker-compose.prod.yml exec api \
  python scripts/fetch_full_quran.py --works all
docker compose -f docker-compose.prod.yml exec api \
  python scripts/build_phrases.py
```

Both are resumable. `build_phrases.py` must run after ingestion, because
re-ingesting a work deletes its clause alignments by cascade, and without them
the reading view shows verses with no commentary attached.

## 7. Check it

```bash
curl -sS https://tafahhum.example.com/api/v1/health
```

## What will not work on the free tier

**Translation.** NLLB needs about 600 MB resident. That fits in 24 GB, so on
the Ampere shape translation does work, unlike on the smaller free tiers. But
CTranslate2's performance on ARM is worse than on x86, so expect translation to
be slower than on your laptop.

**The local generator.** The conclusion is written by a chat model reached over
HTTP. There is no Ollama on the instance, so either point
`TAFAHHUM_ANTHROPIC_API_KEY` at a hosted model or accept that the conclusion is
unavailable in the deployed version. Retrieval, reading, citation and the
evidence view all work regardless: nothing in the chain from source to citation
depends on a generator.

## Before making it public

Two items are not technical and neither is optional.

**Edition licensing is `UNKNOWN` for every work.** The text comes from an open
aggregation that does not identify the underlying print edition. For
pre-modern works the text is usually public domain, but a specific modern
edition may not be, and Ibn Ashur (d. 1973) and al-Uthaymeen (d. 2001) are
recent enough that this is a real question rather than a theoretical one.
Establish the status of each edition before redistributing it publicly.

**Rate limiting is per process.** The limiter holds its counters in memory, so
running more than one API replica multiplies the effective allowance by the
replica count. One replica is correct for this deployment. If you scale out,
move the counters to Redis first.

## Keeping it running

```bash
# Update to the latest images
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Back up the database
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U tafahhum tafahhum | gzip > tafahhum-$(date +%F).sql.gz

# Watch the logs
docker compose -f docker-compose.prod.yml logs -f api
```

Oracle reclaims idle Always Free compute instances. An instance serving real
traffic is not idle, but one sitting untouched for weeks can be flagged, so
keep a monitor hitting the health endpoint if the site is quiet.
