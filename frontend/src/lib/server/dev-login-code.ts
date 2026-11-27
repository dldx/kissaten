// Formats the banner printed to the terminal in development.
export function formatDevVerificationCode(email: string, otp: string): string {
  return `==================================================
  🔑 Kissaten dev login
  email: ${email}
  code:  ${otp}
  (expires in 5 minutes)
==================================================`;
}

// Prints the banner via console.log.
export function printDevVerificationCode(email: string, otp: string): void {
  console.log(formatDevVerificationCode(email, otp));
}
