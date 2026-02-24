package org.matsim.project;

import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;

import java.util.ArrayList;
import java.util.List;

public class RunShamalgan {

	public static void main(String[] args) {
		boolean enableOtfvis = false;
		boolean enableSimwrapper = false;
		List<String> configArgs = new ArrayList<>();

		if (args != null) {
			for (String arg : args) {
				if ("--otfvis".equalsIgnoreCase(arg)) {
					enableOtfvis = true;
				} else if ("--simwrapper".equalsIgnoreCase(arg)) {
					enableSimwrapper = true;
				} else {
					configArgs.add(arg);
				}
			}
		}

		if (configArgs.isEmpty()) {
			configArgs.add("scenarios/shamalgan/config.xml");
		}

		Config config = ConfigUtils.loadConfig(configArgs.toArray(new String[0]));
		RunMatsim.run(config, enableOtfvis, enableSimwrapper);
	}
}
