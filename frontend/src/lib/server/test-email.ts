/**
 * Test script for sending emails using the configured nodemailer transporter
 *
 * Usage:
 * 1. Make sure your .env file has the required SMTP_* variables configured
 * 2. Run this script from the frontend directory:
 *    bun run src/lib/server/test-email.ts
 *
 * You can customize the recipient, subject, and body by modifying the testEmail function call
 */

// Load environment variables from .env file
import { config } from 'dotenv';
import { resolve } from 'path';

// Load .env from the frontend directory
config({ path: resolve(process.cwd(), '.env') });

import { sendEmail, createEmailTransporter } from './email';

/**
 * Verifies SMTP connection without sending an email
 */
async function verifyConnection() {
	console.log('Verifying SMTP connection...');
	const transporter = createEmailTransporter();

	try {
		await transporter.verify();
		console.log('✅ SMTP connection verified successfully!');
		return true;
	} catch (error) {
		console.error('❌ SMTP connection verification failed:', error);
		return false;
	}
}

/**
 * Sends a test email
 */
async function sendTestEmail(to: string) {
	console.log(`Sending test email to ${to}...`);

	try {
		const info = await sendEmail({
			to,
			subject: 'Test Email from Kissaten',
			text: 'This is a test email sent from the Kissaten application.',
			html: `
				<h1>Test Email</h1>
				<p>This is a test email sent from the <strong>Kissaten</strong> application.</p>
				<p>If you received this email, your email configuration is working correctly!</p>
				<hr>
				<p><em>Sent at: ${new Date().toLocaleString()}</em></p>
			`
		});

		console.log('✅ Test email sent successfully!');
		console.log('Message ID:', info.messageId);
		return true;
	} catch (error) {
		console.error('❌ Failed to send test email:', error);
		return false;
	}
}

/**
 * Main test function
 */
async function main() {
	// Get recipient email from command line args or use default
	const recipientEmail = process.argv[2] || process.env.SMTP_USER;

	if (!recipientEmail) {
		console.error('❌ Please provide a recipient email address:');
		console.error('   bun run src/lib/server/test-email.ts your-email@example.com');
		process.exit(1);
	}

	console.log('=== Kissaten Email Test ===\n');

	// First, verify the connection
	const connectionOk = await verifyConnection();

	if (!connectionOk) {
		console.error('\n❌ Cannot proceed with sending test email due to connection issues.');
		console.error('Please check your SMTP configuration in .env file.');
		process.exit(1);
	}

	console.log('');

	// Then send a test email
	const emailSent = await sendTestEmail(recipientEmail);

	if (emailSent) {
		console.log('\n✅ Email test completed successfully!');
		process.exit(0);
	} else {
		console.error('\n❌ Email test failed.');
		process.exit(1);
	}
}

// Run the test
main();
