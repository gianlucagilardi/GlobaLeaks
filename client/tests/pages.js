exports.receiver = function() {
  this.viewMostRecentSubmission = async function() {
    await element(by.id("tip-0")).click();
  };

  this.addPublicKey = async function(pgp_key_path) {
    await browser.setLocation("/recipient/preferences");

    if (browser.gl.utils.testFileUpload()) {
      await element(by.xpath("//input[@type='file']")).sendKeys(pgp_key_path);
    } else {
      var fs = require("fs");
      var pgp_key = fs.readFileSync(pgp_key_path, {encoding: "utf8", flag: "r"});
      var pgpTxtArea = element(by.model("preferences.pgp_key_public"));
      await pgpTxtArea.clear();
      await pgpTxtArea.sendKeys(pgp_key);
    }

    await element.all(by.cssContainingText("span", "Save")).first().click();
  };

  this.wbfile_widget = function() {
    return element(by.css("#TipPageWBFileUpload"));
  };

  this.uploadWBFile = async function(fname) {
    await element(by.xpath("//input[@type='file']")).sendKeys(fname);
  };
};

exports.whistleblower = function() {
  this.performSubmission = async function(title, uploadFiles) {
    var pow = function() {
      return element(by.id("SubmissionForm")).evaluate("submission").then(function(submission) {
        return submission.pow === true;
      });
    };

    await browser.get("/#/submission");

    await browser.gl.utils.waitUntilPresent(by.id("SubmissionForm"));

    await element(by.id("step-receiver-selection")).element(by.id("receiver-0")).click();
    await element(by.id("step-receiver-selection")).element(by.id("receiver-1")).click();
    await element(by.id("NextStepButton")).click();
    await element(by.id("step-0")).element(by.id("step-0-field-0-0-input-0")).sendKeys(title);
    await element(by.id("step-0")).element(by.id("step-0-field-1-0-input-0")).sendKeys("x y z");

    if (uploadFiles && browser.gl.utils.testFileUpload()) {
      var fileToUpload1 = browser.gl.utils.makeTestFilePath("antani.txt");
      var fileToUpload2 = browser.gl.utils.makeTestFilePath("unknown.filetype");
      await element(by.id("step-0")).element(by.id("step-0-field-2-0")).element(by.xpath("//input[@type='file']")).sendKeys(fileToUpload1);
      await element(by.id("step-0")).element(by.id("step-0-field-2-0")).element(by.xpath("//input[@type='file']")).sendKeys(fileToUpload2);
    }

    var submit_button = element(by.id("SubmitButton"));
    var isClickable = protractor.ExpectedConditions.elementToBeClickable(submit_button);
    await browser.wait(isClickable);
    await submit_button.click();

    await browser.gl.utils.waitUntilPresent(by.id("KeyCode"));

    return await element(by.id("KeyCode")).getText();
  };

  this.submitFile = async function(fname) {
    await element(by.xpath("//input[@type='file']")).sendKeys(fname);
  };
};
