from string import Template
import os
from dotenv import load_dotenv

load_dotenv()

# Choose between 'sqlite' or 'mongodb'
DB_NAME = os.getenv("DB_NAME", "test").lower()


new_signin_warning_template_string=Template("""
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>A New Login </title>
    <!--[if !mso]><!-- -->
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <!--<![endif]-->
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style type="text/css">
      #outlook a { padding: 0; }
      .ReadMsgBody { width: 100%; }
      .ExternalClass { width: 100%; }
      .ExternalClass * { line-height: 100%; }
      body {
        margin: 0;
        padding: 0;
        -webkit-text-size-adjust: 100%;
        -ms-text-size-adjust: 100%;
      }
      table, td {
        border-collapse: collapse;
        mso-table-lspace: 0pt;
        mso-table-rspace: 0pt;
      }
      img {
        border: 0;
        height: auto;
        line-height: 100%;
        outline: none;
        text-decoration: none;
        -ms-interpolation-mode: bicubic;
      }
      p { display: block; margin: 13px 0; }
    </style>

    <!--[if !mso]><!-->
    <style type="text/css">
      @media only screen and (max-width: 480px) {
        @-ms-viewport { width: 320px; }
        @viewport { width: 320px; }
      }
    </style>
    <!--<![endif]-->

    <!--[if mso]>
    <xml>
      <o:OfficeDocumentSettings>
        <o:AllowPNG />
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
    <![endif]-->

    <!--[if lte mso 11]>
    <style type="text/css">
      .outlook-group-fix {
        width: 100% !important;
      }
    </style>
    <![endif]-->

    <style type="text/css">
      @media only screen and (min-width: 480px) {
        .mj-column-per-100 {
          width: 100% !important;
          max-width: 100%;
        }
      }
      @media only screen and (max-width: 480px) {
        table.full-width-mobile { width: 100% !important; }
        td.full-width-mobile { width: auto !important; }
      }

      h1 {
        font-family: -apple-system, system-ui, BlinkMacSystemFont;
        font-size: 24px;
        font-weight: 600;
        line-height: 24px;
        text-align: left;
        color: #333333;
        padding-bottom: 18px;
      }
      p {
        font-family: -apple-system, system-ui, BlinkMacSystemFont;
        font-size: 15px;
        font-weight: 300;
        line-height: 24px;
        text-align: left;
        color: #333333;
      }
      a {
        color: #0867ec;
        font-weight: 400;
      }
      a.footer-link {
        color: #888888;
      }
      strong {
        font-weight: 500;
      }
    </style>
  </head>

  <body style="background-color: #ffffff">
    <div style="display: none; font-size: 1px; color: #ffffff; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
      Your $DB_NAME account has been accessed from a new IP address
    </div>

    <div style="background-color: #ffffff">
      <!--[if mso | IE]>
      <table align="center" border="0" cellpadding="0" cellspacing="0" style="width:600px;" width="600">
        <tr><td style="line-height:0px;font-size:0px;mso-line-height-rule:exactly;">
      <![endif]-->

      <div style="background: #ffffff; background-color: #ffffff; margin: 0px auto; max-width: 600px;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" role="presentation" style="background: #ffffff; background-color: #ffffff; width: 100%">
          <tbody>
            <tr>
              <td style="direction: ltr; font-size: 0px; padding: 20px 0; text-align: center; vertical-align: top;">
                <!--[if mso | IE]>
                <table role="presentation" border="0" cellpadding="0" cellspacing="0"><tr><td style="vertical-align:top;width:600px;">
                <![endif]-->

                <div class="mj-column-per-100 outlook-group-fix" style="font-size: 13px; text-align: left; direction: ltr; display: inline-block; vertical-align: top; width: 100%;">
                  <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="vertical-align: top;" width="100%">
                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <table border="0" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse: collapse; border-spacing: 0px;">
                          <tbody>
                            <tr>
                              <td style="width: 54px; border-radius: 100%; ">
                                <img style=" width: 100%; height: 100%;  border-radius: 20%; transform-origin: center center; transform: scale(1.0); " alt="$DB_NAME logo"  height="auto" src="$helpful_img" style="border: 0; display: block; outline: none; text-decoration: none; height: auto; width: 100%;" width="24" />
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>

                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px 24px 25px; word-break: break-word;">
                        <div style="font-family: -apple-system, system-ui, BlinkMacSystemFont; font-size: 15px; font-weight: 300; line-height: 24px; text-align: left; color: #333333;">
                          <h1>We've noticed a new login</h1>
                          <p>Hi $firstName $lastName,</p>
                          <p>This is a routine security alert. Someone logged into your $DB_NAME account from a new IP address:</p>
                          <p>
                            <strong>Time:</strong> $time_data<br />
                            <strong>IP address:</strong> $ip_address<br />
                            <strong>Location:</strong> $location<br />
                            <strong>More Information:</strong> $extra_data
                          </p>
                          <p>If this was you, you can ignore this alert. If you noticed any suspicious activity on your account, please change your password on your email login and on your account page.</p>
                        </div>
                      </td>
                    </tr>

                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <div style="font-family: -apple-system, system-ui, BlinkMacSystemFont; font-size: 15px; font-weight: 300; line-height: 24px; text-align: left; color: #333333;">
                          So long, and thanks for all the fish,<br />
                          <strong>The $DB_NAME Team</strong>
                        </div>
                      </td>
                    </tr>

                    <tr>
                      <td style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <p style="border-top: solid 1px #e8e8e8; font-size: 1; margin: 0px auto; width: 100%;"></p>
                        <!--[if mso | IE]>
                        <table align="center" border="0" cellpadding="0" cellspacing="0" style="border-top: solid 1px #e8e8e8; font-size: 1; margin: 0px auto; width: 550px;" role="presentation" width="550px">
                          <tr><td style="height: 0; line-height: 0">&nbsp;</td></tr>
                        </table>
                        <![endif]-->
                      </td>
                    </tr>

                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <div style="font-family: -apple-system, system-ui, BlinkMacSystemFont; font-size: 12px; font-weight: 300; line-height: 24px; text-align: left; color: #888888;">
                          Somewhere Between Coffee & Code, Quiet Meadows, Earth 00000<br />
                          © 2025 $DB_NAME. LLC
                        </div>
                      </td>
                    </tr>

                    <tr>
                      <td align="left" style="font-size: 0px; padding: 10px 25px; word-break: break-word;">
                        <div style="font-family: -apple-system, system-ui, BlinkMacSystemFont; font-size: 12px; font-weight: 300; line-height: 24px; text-align: left; color: #888888;">
                          For questions contact <a href="mailto:support@x.ai" class="footer-link">support@$DB_NAME.com.ng</a>
                        </div>
                      </td>
                    </tr>
                  </table>
                </div>

                <!--[if mso | IE]></td></tr></table><![endif]-->
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <!--[if mso | IE]></td></tr></table><![endif]-->
    </div>
  </body>
</html>


""")

def generate_new_signin_warning_email_from_template(firstName,lastName,time_data,ip_address,location,extra_data):
    generated_email = new_signin_warning_template_string.safe_substitute(DB_NAME=DB_NAME,helpful_img="https://iili.io/3DKqndN.jpg",firstName=firstName,lastName=lastName,time_data=time_data,ip_address=ip_address,location=location,extra_data=extra_data )
    return generated_email