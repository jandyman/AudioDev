import UIKit

class PatchesVc: UIViewController, UITableViewDelegate, UITableViewDataSource {

  @IBOutlet weak var tableView: UITableView!
  @IBOutlet weak var txtNewFilename: UITextField!

  let audioPath = AudioPath.shared
  let au = AudioPath.shared.au

  override func viewDidLoad() {
    super.viewDidLoad()

    tableView.delegate = self
    tableView.dataSource = self

    let nc = NotificationCenter.default
    nc.addObserver(forName: .didUpdateParameters,
                   object:nil, queue:nil,
                   using:UpdateUi)
  }

  override func didReceiveMemoryWarning() {
    super.didReceiveMemoryWarning()
    // Dispose of any resources that can be recreated.
  }

  func selectRow(row: Int) {
    tableView.selectRow(at: IndexPath(item:row, section:0), animated: false,
                        scrollPosition:UITableView.ScrollPosition.none);
  }

  func UpdateUi(notification: Notification? = nil) {
    tableView.reloadData()
  }

  // MARK: - Table view data source

  func numberOfSections(in tableView: UITableView) -> Int {
    return 1
  }

  func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
    return AudioPath.getPatchFilenames().count
  }

  func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
    let cell = UITableViewCell()
    cell.textLabel!.text = AudioPath.getPatchFilenames()[indexPath.row]
    return cell
  }

  func tableView(_ tableView: UITableView, didSelectRowAt: IndexPath) {
    // SetPreset(newPreset: didSelectRowAt.row)
  }

  func selectedFilename() -> String? {
    if let row = tableView.indexPathForSelectedRow {
      if let cell = tableView.cellForRow(at: row) {
        return cell.textLabel!.text!
      }
    }
    return nil
  }

  @IBAction func loadButtonPressed(_ sender: UIButton) {
    if let filename = selectedFilename() {
      audioPath.loadSettings(baseName: filename)
    }
  }


  @IBAction func saveButtonPressed(_ sender: UIButton) {
    if let filename = selectedFilename() {
      audioPath.saveSettings(baseName: filename)
    }
  }

  @IBAction func newButtonPressed(_ sender: UIButton) {
    if let filename = txtNewFilename.text {
      audioPath.saveSettings(baseName: filename)
      tableView.reloadData()
    }
  }


}
