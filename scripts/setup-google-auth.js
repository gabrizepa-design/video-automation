const { google } = require('googleapis');
const readline = require('readline');

const CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob';

const SCOPES = [
  'https://www.googleapis.com/auth/drive',
  'https://www.googleapis.com/auth/youtube.upload',
  'https://www.googleapis.com/auth/youtube'
];

async function main() {
  const oauth2Client = new google.auth.OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);
  const authUrl = oauth2Client.generateAuthUrl({ access_type: 'offline', scope: SCOPES, prompt: 'consent' });

  console.log('\n=== PASO 1: Abre este URL en tu navegador ===\n');
  console.log(authUrl);
  console.log('\n=== PASO 2: Aprueba permisos y copia el codigo ===\n');

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  rl.question('Codigo de autorizacion: ', async (code) => {
    rl.close();
    try {
      const { tokens } = await oauth2Client.getToken(code.trim());
      console.log('\n=== REFRESH TOKEN ===');
      console.log('GOOGLE_REFRESH_TOKEN=' + tokens.refresh_token);
      require('fs').writeFileSync('google-credentials.txt', 'GOOGLE_REFRESH_TOKEN=' + tokens.refresh_token);
      console.log('\nGuardado en google-credentials.txt');
      oauth2Client.setCredentials(tokens);
      const drive = google.drive({ version: 'v3', auth: oauth2Client });
      const r = await drive.about.get({ fields: 'user' });
      console.log('Cuenta: ' + r.data.user.emailAddress);
    } catch (e) { console.error('Error:', e.message); }
  });
}
main().catch(console.error);
