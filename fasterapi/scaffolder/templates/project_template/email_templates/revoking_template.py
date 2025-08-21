from string import Template
import logging

# --- Revoke Invitation Email Template ---
revoke_invitation_template_string = Template("""
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=US-ASCII">
  <title>Invitation Revoked for ${project_name}</title>
</head>
<body bgcolor="#fafafa" topmargin="0" leftmargin="0" marginheight="0" marginwidth="0" style="width: 100% !important; min-width: 100%; -webkit-font-smoothing: antialiased; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; background-color: #fafafa; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; text-align: center; line-height: 20px; font-size: 14px; margin: 0; padding: 0;">
  <table class="body" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; height: 100%; width: 100%; background-color: #fafafa; padding: 20px 0;" bgcolor="#fafafa">
    <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
      <td class="center" align="center" valign="top" style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;">
        <center style="width: 100%; min-width: 580px;">
          <table class="container" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: inherit; width: 580px; margin: 0 auto; padding: 0;">
            <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
              <td style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0;" align="center" valign="top">
                <div class="panel" style="background: #ffffff; background-color: #ffffff; border-radius: 3px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); padding: 30px; border: 1px solid #dddddd;">
                  <table class="twelve columns" style="border-spacing: 0; border-collapse: collapse; vertical-align: top; text-align: center; width: 100%; margin: 0 auto; padding: 0;">
                    <tr style="vertical-align: top; text-align: center; padding: 0;" align="center">
                      <td style="word-break: break-word; -webkit-hyphens: auto; -moz-hyphens: auto; hyphens: auto; border-collapse: collapse !important; vertical-align: top; text-align: center; color: #333333; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: normal; line-height: 20px; font-size: 14px; margin: 0; padding: 0px 0px 0;" align="center" valign="top">
                        <div class="email-content">
                          <h1 class="primary-heading" style="color: #d9534f; font-family: 'Helvetica Neue',Helvetica,Arial,sans-serif; font-weight: 300; text-align: center; line-height: 1.2; word-break: normal; font-size: 24px; margin: 10px 0 25px; padding: 0;" align="center">Invitation Revoked</h1>
                          <p style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: normal; color: #333; line-height: 24px; text-align: center; margin: 15px 0 25px; padding: 0;" align="center">
                            Your invitation to collaborate on the <strong>${project_name}</strong> project has been revoked by <b>${revoked_by_email}</b>.
                          </p>
                          <p class="email-body-subtext" style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 13px; font-weight: normal; color: #777; line-height: 20px; text-align: center; margin: 15px 0 5px; padding: 0;" align="center">
                            If you believe this was a mistake, please contact the person who invited you directly.
                          </p>
                          <hr class="rule" style="color: #d9d9d9; background-color: #d9d9d9; height: 1px; margin: 30px 0; border-style: none;">
                          <p class="email-text-small email-text-gray" style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; font-weight: normal; color: #777777; line-height: 20px; text-align: center; margin: 15px 0 5px; padding: 0;" align="center">
                            This notification was intended for <strong>${revoked_user_email}</strong>.
                          </p>
                        </div>
                      </td>
                    </tr>
                  </table>
                </div>
              </td>
            </tr>
          </table>
        </center>
      </td>
    </tr>
  </table>
</body>
</html>
""")

def generate_revoke_invitation_email_from_template(
    revoked_user_email: str,
    revoked_by_email: str,
    project_name: str
) -> str:
    """
    Generates an invitation revocation email from a template.
    """
    try:
        return revoke_invitation_template_string.substitute(
            revoked_user_email=revoked_user_email,
            revoked_by_email=revoked_by_email,
            project_name=project_name
        )
    except KeyError as e:
        logging.error(f"Error: Missing template variable: {e}")
        return None

# --- Example Usage ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # --- Generating a test revoke invitation email ---
    test_revoked_user_email = "recipient@example.com"
    test_revoked_by_email = "admin@example.com"
    test_project_name = "Project Alpha"

    print("Generating a test 'revoke invitation' email...")
    email_html = generate_revoke_invitation_email_from_template(
        revoked_user_email=test_revoked_user_email,
        revoked_by_email=test_revoked_by_email,
        project_name=test_project_name
    )

    if email_html:
        print("Email HTML generated successfully:")
        # print(email_html) # Uncomment to see the full HTML output
    else:
        print("Failed to generate email HTML.")
