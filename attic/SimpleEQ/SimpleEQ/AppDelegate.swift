//
//  AppDelegate.swift
//  SimpleEQ
//
//  Created by Andrew Voelkel on 3/27/19.
//  Copyright © 2019 Andrew Voelkel. All rights reserved.
//

import UIKit

let logger = OSLog(subsystem: "AWV.SimpleEQ", category: "General")

extension Notification.Name {
  static let didUpdateParameters = Notification.Name("didUpdateParameters")
}

func Log(_ msg: StaticString) { os_log(msg, log:logger) }

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {
  var window: UIWindow?

  func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
    // Override point for customization after application launch.
    return true
  }

  func applicationWillResignActive(_ application: UIApplication) {
    Log("Will Resign Active")
    // Sent when the application is about to move from active to inactive state. This can occur for certain types of temporary interruptions (such as an incoming phone call or SMS message) or when the user quits the application and it begins the transition to the background state.
    // Use this method to pause ongoing tasks, disable timers, and invalidate graphics rendering callbacks. Games should use this method to pause the game.
  }

  func applicationDidEnterBackground(_ application: UIApplication) {
    Log("Did Enter Foreground")
    // Use this method to release shared resources, save user data, invalidate timers, and store enough application state information to restore your application to its current state in case it is terminated later.
    // If your application supports background execution, this method is called instead of applicationWillTerminate: when the user quits.
  }

  func applicationWillEnterForeground(_ application: UIApplication) {
    Log("SimpleEQ entering foreground")
    // Called as part of the transition from the background to the active state; here you can undo many of the changes made on entering the background.
  }

  func applicationDidBecomeActive(_ application: UIApplication) {
    Log("SimpleEQ did become active")
    // Restart any tasks that were paused (or not yet started) while the application was inactive. If the application was previously in the background, optionally refresh the user interface.
  }

  func applicationWillTerminate(_ application: UIApplication) {
    Log("Will Terminate")
    AudioPath.shared.saveSettings(baseName: "settings.txt")
  }


}

