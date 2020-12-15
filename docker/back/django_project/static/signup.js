// ユーザープールの設定
const poolData = {
    UserPoolId: [ユーザープールID],
    ClientId: [アプリクライアントID]
};
const userPool = new AmazonCognitoIdentity.CognitoUserPool(poolData);

var attributeList = [];

/**
 * 画面読み込み時の処理
 */
$(document).ready(function () {

    // Amazon Cognito 認証情報プロバイダーの初期化
    AWSCognito.config.region = 'ap-northeast-1'; // リージョン
    AWSCognito.config.credentials = new AWS.CognitoIdentityCredentials({
        IdentityPoolId: [IDプールのID]
    });

    // 「Create Account」ボタン押下時
    $("#createAccount").click(function (event) {
        signUp();
    });
});

/**
 * サインアップ処理。
 */
var signUp = function () {

    var username = $("#email").val();
    var lastName = $("#lastName").val();
    var firstName = $("#firstName").val();
    var password = $("#password").val();

    // 何か1つでも未入力の項目がある場合、処理終了
    if (!username | !lastName | !firstName | !password) {
        return false;
    }

    // ユーザ属性リストの生成
    var dataFamilyName = {
        Name: "family_name",
        Value: lastName
    }
    var dataGivenName = {
        Name: "given_name",
        Value: firstName
    }
    var attributeFamilyName = new AmazonCognitoIdentity.CognitoUserAttribute(dataFamilyName);
    var attributeGivenName = new AmazonCognitoIdentity.CognitoUserAttribute(dataGivenName);

    attributeList.push(attributeFamilyName);
    attributeList.push(attributeGivenName);

    // サインアップ処理
    userPool.signUp(username, password, attributeList, null, function (err, result) {
        if (err) {
            alert(err);
            return;
        } else {
            // サインアップ成功の場合、アクティベーション画面に遷移する
        }
    });
}