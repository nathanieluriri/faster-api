from string import Template
# --- Invitation Email Template ---
invitation_template_string = Template("""
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=US-ASCII">
  <title>You're Invited to Collaborate on ${project_name}</title>
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
                          <h1 class="primary-heading" style="color: #333; font-family: 'Helvetica Neue',Helvetica,Arial,sans-serif; font-weight: 300; text-align: center; line-height: 1.2; word-break: normal; font-size: 24px; margin: 10px 0 25px; padding: 0;" align="center">You've Been Invited!</h1>
                          <p style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; font-weight: normal; color: #333; line-height: 24px; text-align: center; margin: 15px 0 25px; padding: 0;" align="center">
                            <b>${inviter_email}</b> has invited you to collaborate on the <strong>${project_name}</strong> project.
                          </p>
                          <div style="text-align: center; color: #ffffff; padding: 20px 0 25px;" align="center">
                            <a href="${register_link}" style="display: inline-block; color: #fff; font-size: 16px; font-weight: 600; background-color: #4183C4; text-decoration: none; text-align: center; border-radius: 5px; -webkit-border-radius: 5px; box-shadow: 0px 3px 0px #25588c; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; -webkit-text-size-adjust: none; margin: 0 auto; padding: 12px 24px;">Accept Invitation</a>
                          </div>
                          <p class="email-body-subtext" style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 13px; font-weight: normal; color: #777; line-height: 20px; text-align: center; margin: 15px 0 5px; padding: 0;" align="center">
                            This invitation will expire in 7 days.
                          </p>
                          <hr class="rule" style="color: #d9d9d9; background-color: #d9d9d9; height: 1px; margin: 30px 0; border-style: none;">
                          <p class="email-text-small email-text-gray" style="word-wrap: normal; hyphens: none; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; font-weight: normal; color: #777777; line-height: 20px; text-align: center; margin: 15px 0 5px; padding: 0;" align="center">
                            This invitation was intended for <strong>${invitee_email}</strong>. If you were not expecting this invitation, you can ignore this email.
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

def generate_invitation_email_from_template(
    invitee_email: str,
    inviter_email: str,
    project_name: str,
    register_link: str
) -> str:
    """
    Generates an invitation email from a template, handling potential errors.
    """
    try:
        return invitation_template_string.substitute(
            invitee_email=invitee_email,
            inviter_email=inviter_email,
            project_name=project_name,
            register_link=register_link
        )
    except KeyError as e:
        print(f"Error: Missing template variable: {e}")
        return None
