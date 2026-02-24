/* *********************************************************************** *
 * project: org.matsim.*												   *
 *                                                                         *
 * *********************************************************************** *
 *                                                                         *
 * copyright       : (C) 2008 by the members listed in the COPYING,        *
 *                   LICENSE and WARRANTY file.                            *
 * email           : info at matsim dot org                                *
 *                                                                         *
 * *********************************************************************** *
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *   See also COPYING, LICENSE and WARRANTY file                           *
 *                                                                         *
 * *********************************************************************** */
package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.contrib.otfvis.OTFVisLiveModule;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.config.groups.ControllerConfigGroup;
import org.matsim.core.controler.Controler;
import org.matsim.core.controler.OutputDirectoryHierarchy.OverwriteFileSetting;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.simwrapper.SimWrapperModule;
import org.matsim.api.core.v01.population.Activity;
import org.matsim.api.core.v01.population.PlanElement;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Person;

/**
 * @author nagel
 *
 */
public class RunMatsim{

	public static void main(String[] args) {

		Config config;
		if ( args==null || args.length==0 || args[0]==null ){
			config = ConfigUtils.loadConfig( "scenarios/equil/config.xml" );
		} else {
			config = ConfigUtils.loadConfig( args );
		}

		run(config, false, false);
	}

	public static void run(Config config) {
		run(config, false, false);
	}

	public static void run(Config config, boolean enableOtfvis, boolean enableSimwrapper) {

		config.controller().setOverwriteFileSetting( OverwriteFileSetting.deleteDirectoryIfExists );
		config.controller().setCompressionType(ControllerConfigGroup.CompressionType.none);

		// possibly modify config here

		// ---
		
		Scenario scenario = ScenarioUtils.loadScenario(config) ;
		fillMissingActivityCoordsFromLinks(scenario);

		// possibly modify scenario here
		
		// ---
		
		Controler controler = new Controler( scenario ) ;
		
		// possibly modify controler here

		if (enableOtfvis) {
			controler.addOverridingModule(new OTFVisLiveModule());
		}
		if (enableSimwrapper) {
			controler.addOverridingModule(new SimWrapperModule());
		}
		
		// ---
		
		controler.run();
	}

	private static void fillMissingActivityCoordsFromLinks(Scenario scenario) {
		int fixed = 0;
		for (Person person : scenario.getPopulation().getPersons().values()) {
			for (Plan plan : person.getPlans()) {
				for (PlanElement pe : plan.getPlanElements()) {
					if (pe instanceof Activity act && act.getCoord() == null && act.getLinkId() != null) {
						Link link = scenario.getNetwork().getLinks().get(act.getLinkId());
						if (link != null && link.getCoord() != null) {
							act.setCoord(link.getCoord());
							fixed++;
						}
					}
				}
			}
		}
		System.out.println("Filled missing activity coords from links: " + fixed);
	}
	
}
