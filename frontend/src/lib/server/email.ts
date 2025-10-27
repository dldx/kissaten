import nodemailer from 'nodemailer';
import type { Transporter } from 'nodemailer';

// Utility to get environment variables - works both in SvelteKit and standalone scripts
function getEnv(key: string): string | undefined {
	// Use process.env which works in both contexts
	return process.env[key];
}

/**
 * Creates and returns a nodemailer transporter configured with SMTP settings from environment variables
 *
 * Environment variables required:
 * - SMTP_HOST: SMTP server hostname (e.g., smtp.gmail.com)
 * - SMTP_PORT: SMTP server port (e.g., 587 for TLS, 465 for SSL)
 * - SMTP_USER: SMTP authentication username
 * - SMTP_PASS: SMTP authentication password
 * - SMTP_FROM: Default sender email address
 */
export function createEmailTransporter(): Transporter {
	const smtpHost = getEnv('SMTP_HOST');
	const smtpPort = getEnv('SMTP_PORT');
	const smtpUser = getEnv('SMTP_USER');
	const smtpPass = getEnv('SMTP_PASS');

	if (!smtpHost || !smtpUser || !smtpPass) {
		throw new Error('Missing required SMTP configuration. Please check your .env file.');
	}

	const transporter = nodemailer.createTransport({
		host: smtpHost,
		port: parseInt(smtpPort || '587'),
		secure: parseInt(smtpPort || '587') === 465, // true for 465, false for other ports
		auth: {
			user: smtpUser,
			pass: smtpPass
		}
	});

	return transporter;
}

/**
 * Sends an email using the configured transporter
 *
 * @param to - Recipient email address
 * @param subject - Email subject line
 * @param text - Plain text body (optional if html is provided)
 * @param html - HTML body (optional if text is provided)
 * @returns Promise that resolves when email is sent
 */
export async function sendEmail({
	to,
	subject,
	text,
	html
}: {
	to: string;
	subject: string;
	text?: string;
	html?: string;
}) {
	const transporter = createEmailTransporter();
	const smtpFrom = getEnv('SMTP_FROM');

	if (!smtpFrom) {
		throw new Error('Missing SMTP_FROM configuration. Please check your .env file.');
	}

	const mailOptions = {
		from: smtpFrom,
		to,
		subject,
		text,
		html
	};

	try {
		const info = await transporter.sendMail(mailOptions);
		console.log('Email sent successfully:', info.messageId);
		return info;
	} catch (error) {
		console.error('Error sending email:', error);
		throw error;
	}
}
