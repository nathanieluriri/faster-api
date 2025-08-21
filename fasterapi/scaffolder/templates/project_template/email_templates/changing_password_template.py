from string import Template

changing_password_template_string=Template("""
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Here’s the code to reset your password: $otp_code</title>
  <meta name="format-detection" content="email=no" />
  <meta name="format-detection" content="date=no" />
  <style nonce="DoEqAMc5wqGswLpJhSuEWA">
    .awl a { color: #FFFFFF; text-decoration: none; }
    .abml a { color: #000000; font-family: Roboto-Medium, Helvetica, Arial, sans-serif; font-weight: bold; text-decoration: none; }
    .adgl a { color: rgba(0, 0, 0, 0.87); text-decoration: none; }
    .afal a { color: #b0b0b0; text-decoration: none; }

    @media screen and (min-width: 600px) {
      .v2sp { padding: 6px 30px 0px; }
      .v2rsp { padding: 0px 10px; }
    }

    @media screen and (min-width: 600px) {
      .mdv2rw { padding: 40px 40px; }
    }
     .dark-mode-image {
    display: none; /* Hide the dark mode image by default */
  }
  img {
      filter: invert(100%); /* Inverts colors */
      /* You might need brightness, contrast, hue-rotate etc. */
    }

  /* When the user prefers dark mode */
  @media (prefers-color-scheme: dark) {
    .light-mode-image {
      display: none; /* Hide the light mode image */
    }
    .dark-mode-image {
      display: inline-block; /* Show the dark mode image */
    }
  }
  </style>
  
  <link href="//fonts.googleapis.com/css?family=Google+Sans" rel="stylesheet" type="text/css" nonce="DoEqAMc5wqGswLpJhSuEWA" />
</head>
<body style="margin: 0; padding: 0;" bgcolor="#FFFFFF">

  <table width="100%" height="100%" style="min-width: 348px;" border="0" cellspacing="0" cellpadding="0" lang="en">
    <tr height="32" style="height: 32px;"><td></td></tr>
    <tr align="center">
      <td>
        <div itemscope itemtype="//schema.org/EmailMessage">
          <div itemprop="action" itemscope itemtype="//schema.org/ViewAction">
            <meta itemprop="name" content="Review Activity" />
          </div>
        </div>

        <table border="0" cellspacing="0" cellpadding="0" style="padding-bottom: 20px; max-width: 516px; min-width: 220px;">
          <tr>
            <td width="8" style="width: 8px;"></td>
            <td>
              <div style="background-color: #F5F5F5; direction: ltr; padding: 16px; margin-bottom: 6px;">
                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                  <tbody>
                    <tr>
                      <td style="vertical-align: top;">
                        <img height="20" src="https://www.gstatic.com/accountalerts/email/Icon_recovery_x2_20_20.png" />
                      </td>
                      <td width="13" style="width: 13px;"></td>
                      <td style="direction: ltr;">
                        <span style="font-family: Roboto-Regular, Helvetica, Arial, sans-serif; font-size: 13px; color: rgba(0,0,0,0.54); line-height: 1.6;">
                          Here’s the code to reset your password: $otp_code
                          <a style="text-decoration: none; color: rgba(0,0,0,0.87);">we’ve sent it to $email,</a> the address associated with the account requesting the reset.

                        </span>
                        <span style="font-family: Roboto-Regular, Helvetica, Arial, sans-serif; font-size: 13px; color: rgba(0,0,0,0.54); line-height: 1.6;">
                          If you didn’t request this, you can safely ignore this message.
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div style="border-style: solid; border-width: thin; border-color:#dadce0; border-radius: 8px; padding: 40px 20px;" align="center" class="mdv2rw">
              <img class="dark-mode-image" src="https://iili.io/3DBDnYg.png"
              
     width="90"
     height="50"
     aria-hidden="true"
     style="margin-bottom: 16px; background-color: rgba(0, 0, 0, 1); border-radius: 10%;"
     alt="Mie" />
                   <img class="light-mode-image" src="https://iili.io/3DBDnYg.png"
              
     width="90"
     height="50"
     aria-hidden="true"
     style="margin-bottom: 16px; background-color: rgba(0, 0, 0, 1); border-radius: 10%;"
     alt="Mie" />
                <div style="font-family: 'Google Sans', Roboto, RobotoDraft, Helvetica, Arial, sans-serif; border-bottom: thin solid #dadce0; color: rgba(0,0,0,0.87); line-height: 32px; padding-bottom: 24px; text-align: center; word-break: break-word;">
                  <div style="font-size: 24px;">$otp_code</div>
                  <table align="center" style="margin-top: 8px;">
                    <tr style="line-height: normal;">
                      <td align="right" style="padding-right: 8px;">
                        <img width="20" height="20" style="width: 20px; height: 20px; vertical-align: sub; border-radius: 50%;" src="$avatar" alt="avatar" />
                      </td>
                      <td>
                        <a style="font-family: 'Google Sans', Roboto, RobotoDraft, Helvetica, Arial, sans-serif; color: rgba(0,0,0,0.87); font-size: 14px; line-height: 20px;">$email</a>
                      </td>
                    </tr>
                  </table>
                </div>

                <div style="font-family: Roboto-Regular, Helvetica, Arial, sans-serif; font-size: 14px; color: rgba(0,0,0,0.87); line-height: 20px; padding-top: 20px; text-align: center;">
                  We got a request from you to change your password so please use the otp and change your password. If this was you, you don’t need to do anything. If not, we’ll help you secure your account.
                  </html>


""")

def generate_changing_password_email_from_template(otp_code,user_email,avatar_image_link):
    generated_email = changing_password_template_string.safe_substitute(otp_code=otp_code,email=user_email,avatar=avatar_image_link )
    return generated_email