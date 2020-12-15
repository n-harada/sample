// ユーザープールの設定
const poolData = {
    UserPoolId: [ユーザープールID],
    ClientId: [アプリクライアントID]
};
const userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);

/**
 * 画面読み込み時の処理
 */
$(document).ready(function () {

    // Amazon Cognito 認証情報プロバイダーの初期化
    AWSCognito.config.region = 'ap-northeast-1'; // リージョン
    AWSCognito.config.credentials = new AWS.CognitoIdentityCredentials({
        IdentityPoolId: [IDプールのID]
    });

    // 「Sign In」ボタン押下時
    $("#signinButton").click(function (event) {
        signIn();
    });
});

/**
 * サインイン処理
 */
var signIn = function () {
    var email = $('#email').val();
    var password = $('#password').val();

    // 何か1つでも未入力の項目がある場合、メッセージを表示して処理を中断
    if (!email | !password) {
        $("#signin div#message span").empty();
        $("#signin div#message span").append("All fields are required.");
        return false;
    }

    // 認証データの作成
    var authenticationData = {
        Username: email,
        Password: password
    };
    var authenticationDetails = new AmazonCognitoIdentity.AuthenticationDetails(authenticationData);

    var userData = {
        Username: email,
        Pool: userPool
    };
    var cognitoUser = new AmazonCognitoIdentity.CognitoUser(userData);

    // 認証処理
    cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: function (result) {
            var idToken = result.getIdToken().getJwtToken();          // IDトークン
            var accessToken = result.getAccessToken().getJwtToken();  // アクセストークン
            var refreshToken = result.getRefreshToken().getToken();   // 更新トークン

            console.log("idToken : " + idToken);
            console.log("accessToken : " + accessToken);
            console.log("refreshToken : " + refreshToken);

            // サインイン成功の場合、次の画面へ遷移
        },

        onFailure: function (err) {
            // サインイン失敗の場合、エラーメッセージを画面に表示
            console.log(err);
            $("div#message span").empty();
            $("div#message span").append(err.message);
        }
    });
};